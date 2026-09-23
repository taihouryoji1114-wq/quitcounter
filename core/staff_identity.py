"""Stable staff IDs and display names; PIN values never live in source code."""
import unicodedata

STAFF_NAMES = dict(zip((f"スタッフ{letter}" for letter in "ABCDEFG"),
                      ("Ha", "Na", "Ka", "Sy", "Ma", "Fu", "Si")))


def staff_display_name(staff_id):
    return STAFF_NAMES.get(unicodedata.normalize("NFKC", str(staff_id)), staff_id)


def personal_staff_account(pin):
    from core.shift_submissions import shift_submissions
    matches = [staff_id for staff_id in STAFF_NAMES
               if shift_submissions.verify_staff_pin(staff_id, pin)]
    # A duplicated PIN must not arbitrarily select another person's identity.
    if len(matches) > 1:
        raise ValueError("個人PINが重複しています。管理者に再設定を依頼してください。")
    if not matches:
        return None
    staff_id = matches[0]
    return {"role": "staff", "user_id": "", "staff_id": staff_id,
            "display_name": staff_display_name(staff_id)}
