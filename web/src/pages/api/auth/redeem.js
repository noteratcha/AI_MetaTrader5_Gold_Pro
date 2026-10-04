import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { adjustHours, allowMethods, requireUser } from '../../../lib/server/auth';
import { isValidKeyFormat, normalizeKey } from '../../../lib/server/keys';
import { logActivity } from '../../../lib/server/activity';

/**
 * เติมชั่วโมงด้วย Product Key
 * 1) product_keys — คีย์ที่ได้จากการซื้อผ่าน PromptPay/SlipOK
 * 2) promo_keys   — คีย์โปรโมชันที่ Admin ผลิต
 * การ "จอง" คีย์ทำแบบ atomic (UPDATE ... WHERE ยังไม่ถูกใช้) กันการเติมคีย์เดียวซ้ำพร้อมกัน
 */
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const keyCode = normalizeKey(req.body?.keyCode);
  if (!isValidKeyFormat(keyCode)) {
    return res.status(400).json({ success: false, error: 'กรุณากรอกรหัสให้ครบ 24 หลัก (6 กลุ่ม)' });
  }

  const supabase = getAdminClient();
  const email = auth.user.email;
  const now = new Date().toISOString();

  try {
    let hoursToAdd = null;

    // 1) Product Key จากการซื้อ
    const { data: claimedProduct } = await supabase
      .from('product_keys')
      .update({ is_used: true, status: 'REDEEMED', redeemed_at: now })
      .eq('key_code', keyCode)
      .eq('is_used', false)
      .select('hours, bonus_hours');

    if (claimedProduct && claimedProduct.length === 1) {
      hoursToAdd = Number(claimedProduct[0].hours || 0) + Number(claimedProduct[0].bonus_hours || 0);
      // บันทึกผู้ใช้คีย์ (คอลัมน์จาก migration — ถ้ายังไม่มีจะข้ามไปเงียบ ๆ)
      await supabase.from('product_keys').update({ redeemed_by_email: email }).eq('key_code', keyCode);
    } else {
      // 2) Promo Key จาก Admin
      const { data: promo } = await supabase.from('promo_keys').select('*').eq('key_code', keyCode).maybeSingle();
      if (!promo) {
        const { data: usedProduct } = await supabase.from('product_keys').select('key_code').eq('key_code', keyCode).maybeSingle();
        return res
          .status(usedProduct ? 409 : 404)
          .json({ success: false, error: usedProduct ? 'รหัสนี้ถูกใช้งานไปแล้ว' : 'ไม่พบรหัสนี้ในระบบ' });
      }
      if (promo.used) {
        return res.status(409).json({ success: false, error: 'รหัสนี้ถูกใช้งานไปแล้ว' });
      }
      if (promo.expires_at && new Date(promo.expires_at) < new Date()) {
        return res.status(410).json({ success: false, error: 'รหัสนี้หมดอายุแล้ว' });
      }
      const { data: claimedPromo } = await supabase
        .from('promo_keys')
        .update({ used: true, used_by: email, used_at: now })
        .eq('key_code', keyCode)
        .eq('used', false)
        .select('hours');
      if (!claimedPromo || claimedPromo.length !== 1) {
        return res.status(409).json({ success: false, error: 'รหัสนี้ถูกใช้งานไปแล้ว' });
      }
      hoursToAdd = Number(claimedPromo[0].hours || 0);
    }

    if (!(hoursToAdd > 0)) {
      return res.status(400).json({ success: false, error: 'คีย์นี้ไม่มีชั่วโมงให้เติม' });
    }

    const hoursRemaining = await adjustHours(auth.row.id, hoursToAdd);
    await logActivity({ userId: auth.row.id, email, event: 'redeem', detail: `เติมคีย์ ${keyCode} +${hoursToAdd} ชม. (คงเหลือ ${hoursRemaining.toFixed(2)})` });
    return res.status(200).json({
      success: true,
      message: `เติมชั่วโมงสำเร็จ! ได้รับ +${hoursToAdd} ชั่วโมง (คงเหลือ ${hoursRemaining.toFixed(2)} ชม.)`,
      hoursAdded: hoursToAdd,
      hoursRemaining,
    });
  } catch (err) {
    console.error('[auth/redeem] error:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดในการเติมคีย์ กรุณาลองใหม่' });
  }
}
