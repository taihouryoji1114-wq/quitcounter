"""Questions and temporary business notices shared by the store app."""

from datetime import datetime
from uuid import uuid4

from core.data import data


class StoreQuizManager:
    def __init__(self, data_manager=None):
        self._data_manager = data_manager or data

    def questions(self):
        return [dict(item) for item in self._data_manager.data.get("store_quiz_questions", [])
                if isinstance(item, dict) and item.get("active", True)]

    def add_question(self, question, answer, wrong_answers):
        question = str(question or "").strip()
        answer = str(answer or "").strip()
        wrong = [str(value or "").strip() for value in wrong_answers]
        wrong = [value for value in wrong if value]
        if not question:
            raise ValueError("問題文を入力してください。")
        if not answer:
            raise ValueError("正解を入力してください。")
        if len(wrong) != 3:
            raise ValueError("間違いの選択肢を3つ入力してください。")
        choices = [answer, *wrong]
        if len(set(choices)) != 4:
            raise ValueError("4つの選択肢はすべて違う内容にしてください。")
        item = {
            "id": uuid4().hex, "question": question[:200], "answer": answer[:100],
            "wrong_answers": [value[:100] for value in wrong], "active": True,
            "created_at": datetime.now().isoformat(timespec="minutes"),
        }
        self._data_manager.data.setdefault("store_quiz_questions", []).append(item)
        self._data_manager.save()
        return dict(item)

    def seed_question_pack(self, pack_id, questions):
        """Add an explicitly approved question pack once without replacing user data."""
        pack_id = str(pack_id or "").strip()
        if not pack_id:
            raise ValueError("問題セットIDが必要です。")
        completed = self._data_manager.data.setdefault("store_quiz_question_packs", [])
        if pack_id in completed:
            return 0
        existing = {
            str(item.get("question", "")).strip()
            for item in self._data_manager.data.get("store_quiz_questions", [])
            if isinstance(item, dict) and item.get("active", True)
        }
        added = 0
        for question, answer, wrong_answers in questions:
            if str(question).strip() in existing:
                continue
            self.add_question(question, answer, wrong_answers)
            existing.add(str(question).strip())
            added += 1
        completed.append(pack_id)
        self._data_manager.save()
        return added

    def delete_question(self, question_id):
        for item in self._data_manager.data.setdefault("store_quiz_questions", []):
            if isinstance(item, dict) and item.get("id") == question_id and item.get("active", True):
                item["active"] = False
                self._data_manager.save()
                return
        raise ValueError("問題が見つかりません。")

    def notices(self, include_closed=False):
        return [dict(item) for item in self._data_manager.data.get("store_business_notices", [])
                if isinstance(item, dict)
                and (include_closed or item.get("active", True))]

    def add_notice(self, title, details=""):
        title = str(title or "").strip()
        details = str(details or "").strip()
        if not title:
            raise ValueError("業務連絡の題名を入力してください。")
        item = {
            "id": uuid4().hex, "title": title[:100], "details": details[:1000],
            "active": True, "created_at": datetime.now().isoformat(timespec="minutes"),
            "acknowledgements": [], "explanation_requests": [],
        }
        self._data_manager.data.setdefault("store_business_notices", []).append(item)
        self._data_manager.save()
        return dict(item)

    def respond_to_notice(self, notice_id, staff_name, needs_explanation=False):
        staff_name = str(staff_name or "").strip()
        if not staff_name:
            raise ValueError("スタッフ名を入力してください。")
        response_key = "explanation_requests" if needs_explanation else "acknowledgements"
        opposite_key = "acknowledgements" if needs_explanation else "explanation_requests"
        for item in self._data_manager.data.setdefault("store_business_notices", []):
            if not isinstance(item, dict) or item.get("id") != notice_id:
                continue
            item.setdefault(response_key, [])
            item.setdefault(opposite_key, [])
            item[opposite_key] = [value for value in item[opposite_key]
                                  if value.get("name") != staff_name]
            if not any(value.get("name") == staff_name for value in item[response_key]):
                item[response_key].append({
                    "name": staff_name[:40],
                    "at": datetime.now().isoformat(timespec="minutes"),
                })
            self._data_manager.save()
            return
        raise ValueError("業務連絡が見つかりません。")

    def close_notice(self, notice_id):
        for item in self._data_manager.data.setdefault("store_business_notices", []):
            if isinstance(item, dict) and item.get("id") == notice_id and item.get("active", True):
                item["active"] = False
                item["closed_at"] = datetime.now().isoformat(timespec="minutes")
                self._data_manager.save()
                return
        raise ValueError("業務連絡が見つかりません。")


store_quiz = StoreQuizManager()


CHANKO_DOJO_BASIC_PACK = (
    ("お客様を席へご案内したあと、最初に持っていくものをすべて答えてください。",
     "とんすい、レンゲ、平皿、お通し、ツボ、おしぼり",
     ["とんすい、箸、メニュー、おしぼり", "レンゲ、取り箸、灰皿、お通し", "平皿、鍋敷き、伝票、ツボ"]),
    ("ご案内後に持っていくものは、全部で何種類ですか？", "6種類", ["4種類", "5種類", "7種類"]),
    ("ご案内後に持っていく食器のうち、汁をすくう道具は何ですか？", "レンゲ", ["とんすい", "平皿", "ツボ"]),
    ("ちゃんこは通常、何人前から注文できますか？", "2人前から", ["1人前から", "3人前から", "4人前から"]),
    ("1名様がちゃんこを注文する場合、最低何人前から注文できますか？", "1人前から", ["2人前から", "3人前から", "注文できない"]),
    ("ちゃんこのスープは何をベースにしていますか？", "醤油ベース", ["味噌ベース", "塩ベース", "豚骨ベース"]),
    ("黒豚1人前の基準量は何グラムですか？", "150グラム", ["75グラム", "100グラム", "200グラム"]),
    ("小鍋の黒豚の基準量は何グラムですか？", "75グラム", ["50グラム", "100グラム", "150グラム"]),
    ("黒豚を量るときに認められる誤差は何グラム以内ですか？", "5グラム以内", ["2グラム以内", "10グラム以内", "15グラム以内"]),
    ("黒豚1人前150グラムで、許容範囲として正しいものは？", "145〜155グラム", ["140〜160グラム", "145〜160グラム", "150〜160グラム"]),
    ("小鍋の黒豚75グラムで、許容範囲として正しいものは？", "70〜80グラム", ["65〜85グラム", "70〜85グラム", "75〜85グラム"]),
    ("米を研いで水にさらしたあと、何分放置しますか？", "30分", ["10分", "20分", "60分"]),
    ("唐揚げを1回仕込む肉の量は何キログラムですか？", "2キログラム", ["1キログラム", "1.5キログラム", "3キログラム"]),
    ("唐揚げ2キログラムは何袋分ですか？", "1袋分", ["半袋分", "2袋分", "3袋分"]),
    ("唐揚げの肉は、最初に何分血抜きしますか？", "3分", ["1分", "5分", "10分"]),
    ("唐揚げの味付けに使う調味料をすべて答えてください。",
     "ヤマサ醤油、風月歌、おろししょうが、おろしニンニク",
     ["醤油、酒、砂糖、塩", "ヤマサ醤油、味噌、しょうが、ごま油", "風月歌、塩、こしょう、ニンニク"]),
    ("唐揚げ2キログラムに入れる、おろししょうがの量は？", "スプーン1.5杯", ["スプーン1杯", "スプーン2杯", "スプーン3杯"]),
    ("唐揚げ2キログラムに入れる、おろしニンニクの量は？", "スプーン1.5杯", ["スプーン1杯", "スプーン2杯", "スプーン3杯"]),
    ("唐揚げを味付けして密閉したあと、何分放置しますか？", "30分", ["10分", "20分", "60分"]),
    ("唐揚げを密閉するときの正しい方法は？", "空気が入らないよう肉にラップかリードを貼り付ける",
     ["ボウルの上だけをふんわり覆う", "空気を多く入れて袋を閉じる", "何もかけず冷蔵庫へ入れる"]),
    ("30分漬けた唐揚げは、タレを何分切りますか？", "3分", ["1分", "5分", "10分"]),
    ("タレを切った唐揚げは、片栗粉をどの程度まぶしますか？", "全体が真っ白になるまで",
     ["表面に薄く少量だけ", "半分だけ白くなるまで", "片栗粉は使わない"]),
    ("一月場所の開催地はどこですか？", "東京・国技館", ["大阪・エディオンアリーナ大阪", "名古屋・IGアリーナ", "福岡・福岡国際センター"]),
    ("三月場所の開催地はどこですか？", "大阪・エディオンアリーナ大阪", ["東京・国技館", "名古屋・IGアリーナ", "福岡・福岡国際センター"]),
    ("五月場所の開催地はどこですか？", "東京・国技館", ["大阪・エディオンアリーナ大阪", "名古屋・IGアリーナ", "福岡・福岡国際センター"]),
    ("七月場所の開催地はどこですか？", "名古屋・IGアリーナ", ["東京・国技館", "大阪・エディオンアリーナ大阪", "福岡・福岡国際センター"]),
    ("九月場所の開催地はどこですか？", "東京・国技館", ["大阪・エディオンアリーナ大阪", "名古屋・IGアリーナ", "福岡・福岡国際センター"]),
    ("十一月場所の開催地はどこですか？", "福岡・福岡国際センター", ["東京・国技館", "大阪・エディオンアリーナ大阪", "名古屋・IGアリーナ"]),
    ("東京の国技館で行われる本場所は何月場所ですか？", "一月・五月・九月場所",
     ["一月・三月・五月場所", "三月・七月・十一月場所", "五月・七月・九月場所"]),
    ("大阪で行われる本場所は何月場所ですか？", "三月場所", ["一月場所", "五月場所", "七月場所"]),
    ("名古屋で行われる本場所は何月場所ですか？", "七月場所", ["三月場所", "九月場所", "十一月場所"]),
    ("福岡で行われる本場所は何月場所ですか？", "十一月場所", ["一月場所", "七月場所", "九月場所"]),
)

TSUKUNE_PREP_PACK = (
    ("つくねをひき肉6キログラムで仕込むとき、卵は何個入れますか？", "5個", ["3個", "4個", "6個"]),
    ("つくねをひき肉6キログラムで仕込むとき、ごま油はどのくらい入れますか？", "2周", ["1周", "3周", "150cc"]),
    ("つくねをひき肉6キログラムで仕込むとき、醤油と風月歌はそれぞれどのくらい入れますか？",
     "150ccレードルですり切り2杯", ["150ccレードルですり切り1杯", "150ccレードルですり切り3杯", "計量せず適量"]),
    ("つくねの仕込みで小麦粉を入れるときの正しい方法は？",
     "混ぜながら様子を見て適量を入れる", ["最初に1袋すべて入れる", "小麦粉は入れない", "最後に表面だけへまぶす"]),
)

SERVICE_AND_TABLE_PACK = (
    ("レジ会計を始める前に、最初に何を確認しますか？",
     "ポイント控除や特別指示を確認するためのボード", ["レジの現金残高", "予約台帳", "厨房の仕込み表"]),
    ("店内の卓番は何番から何番までですか？", "1番から15番まで", ["1番から12番まで", "1番から16番まで", "0番から15番まで"]),
    ("座敷テーブルの卓番の組み合わせはどれですか？", "1〜4番と9〜12番", ["1〜8番", "5〜8番と13〜15番", "9〜15番"]),
    ("椅子テーブルの卓番の組み合わせはどれですか？", "5〜8番と13〜15番", ["1〜4番と9〜12番", "1〜8番", "9〜15番"]),
    ("レモンサワーの分量は何プッシュですか？", "1プッシュ", ["2プッシュ", "半プッシュ", "3プッシュ"]),
    ("角ハイボールの分量は何プッシュですか？", "1プッシュ", ["2プッシュ", "半プッシュ", "3プッシュ"]),
    ("あんず・巨峰・グレープフルーツ・梅酒・すだちサワーを作る正しい順番は？",
     "氷→炭酸7割→原液3割", ["氷→原液7割→炭酸3割", "原液→氷→炭酸", "炭酸→原液→氷"]),
    ("ちゃんこの器は、何人前まで用意されていますか？", "1〜4人前", ["1〜3人前", "2〜4人前", "2〜5人前"]),
    ("ちゃんこの具材（野菜）を盛る入れ物は何ですか？", "すり鉢", ["平皿", "とんすい", "ボウル"]),
    ("野菜だけを盛ったちゃんこの具材を何と呼びますか？", "ザク", ["ネタ", "タネ", "アテ"]),
    ("『ザク1人前』の正しい意味は？", "1人前のすり鉢に入った具材（野菜）", ["刻んだ野菜1種類", "1人前の肉だけ", "小鍋に入った完成品"]),
)

store_quiz.seed_question_pack("chanko_dojo_basic_20260826", CHANKO_DOJO_BASIC_PACK)
store_quiz.seed_question_pack("chanko_tsukune_20260830", TSUKUNE_PREP_PACK)
store_quiz.seed_question_pack("chanko_service_tables_20260906", SERVICE_AND_TABLE_PACK)
