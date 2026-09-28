import unittest
from app.rag import KnowledgeBase, normalize
from app.server import direct_answer, web_fallback_kind


class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()

    def test_normalization(self):
        self.assertEqual(normalize("Соляная Ё-камера!"), "соляная е камера")

    def test_price_retrieval(self):
        hits = self.kb.search("Сколько стоит соляная камера?")
        self.assertIn("300 руб", hits[0].content)

    def test_generic_massage_price_is_concise(self):
        answer = self.kb.price_answer("Сколько стоит массаж?")
        self.assertIn("видов массажа", answer)
        self.assertIn("Уточните", answer)
        self.assertNotIn("Сервис временно", answer)

    def test_misspelled_massage_is_understood(self):
        self.assertIn("видов массажа", self.kb.price_answer("Сколько стоит масаж?"))

    def test_specific_massage_price(self):
        answer = self.kb.price_answer("Цена массажа спины")
        self.assertIn("700 ₽", answer)
        self.assertIn("20 мин", answer)

    def test_package_retrieval(self):
        hits = self.kb.search("цена путевки двухместный номер")
        self.assertIn("5100", hits[0].content)

    def test_natural_package_question_retrieval(self):
        context, hits = self.kb.context("Сколько будет стоить отдых с лечением и питанием на 5 дней?")
        self.assertTrue(context)
        self.assertIn("5100", hits[0].content)

    def test_greeting_and_capabilities_do_not_need_rag(self):
        self.assertIn("Здравствуйте", direct_answer("Привет!"))
        self.assertIn("путев", direct_answer("Привет! Что ты умеешь?"))

    def test_five_day_package_is_calculated(self):
        answer = direct_answer("Сколько будет стоить отдых с лечением и питанием на 5 дней?")
        self.assertIn("25 500 ₽", answer)
        self.assertIn("одного человека", answer)

    def test_accommodation_price(self):
        self.assertIn("2 000 ₽", direct_answer("Сколько стоит проживание?"))

    def test_common_overview_questions(self):
        self.assertIn("физиотерапия", direct_answer("Какие процедуры есть в санатории?"))
        self.assertIn("посёлке Энергетик", direct_answer("Расскажи о санатории"))

    def test_controlled_web_fallback_classification(self):
        self.assertEqual(web_fallback_kind("Что такое карбокситерапия?"), "medical")
        self.assertEqual(web_fallback_kind("Есть ли трансфер в санаторий?"), "official")
        self.assertIsNone(web_fallback_kind("Кто выиграл вчера матч?"))

    def test_unavailable_status(self):
        hits = self.kb.search("работает ли сауна")
        combined = " ".join(h.content for h in hits[:3])
        self.assertIn("недоступна", combined)

    def test_unknown_question_has_no_context(self):
        context, _ = self.kb.context("Есть ли у вас вертолетная площадка?")
        self.assertEqual(context, "")

    def test_tourist_tax_retrieval(self):
        context, _ = self.kb.context("Какой туристический налог в Энергетике?")
        self.assertIn("100 рублей", context)

    def test_base_program_counts_retrieval(self):
        context, hits = self.kb.context("Сколько массажей входит в путевку на 14 дней?")
        self.assertIn("10/8/6", context)
        self.assertEqual(hits[0].title, "Количество процедур по длительности путевки")


if __name__ == "__main__":
    unittest.main()
