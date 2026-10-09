import unittest
from unittest.mock import patch
from app.rag import KnowledgeBase, normalize
from app.server import direct_answer, local_answer_from_hits, web_fallback_kind


class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()

    def test_normalization(self):
        self.assertEqual(normalize("Соляная Ё-камера!"), "соляная е камера")

    def test_price_retrieval(self):
        hits = self.kb.search("Сколько стоит соляная камера?")
        self.assertIn("300 руб", hits[0].content)

    def test_strong_lexical_match_does_not_call_embeddings(self):
        with patch("app.rag.embed", side_effect=AssertionError("embedding must not be called")):
            hits = self.kb.search("Сколько стоит плазмолифтинг?")
        self.assertEqual(hits[0].title, "Плазмолифтинг")

    def test_local_fallback_uses_retrieved_fact(self):
        hits = self.kb.search("Сколько стоит плазмолифтинг?")
        answer = local_answer_from_hits(hits)
        self.assertIn("2000 руб", answer)
        self.assertNotIn("Сервис временно недоступен", answer)
        self.assertNotIn("01.06.2025", answer)

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

    def test_exact_non_massage_price_is_local(self):
        answer = self.kb.price_answer("Сколько стоит плазмолифтинг?")
        self.assertIn("2 000 ₽", answer)
        self.assertNotIn("01.06.2025", answer)

    def test_generic_procedure_prices_only_show_available_examples(self):
        answer = self.kb.price_answer("Привет! Сколько стоят процедуры?")
        self.assertIn("Стоимость зависит от конкретной процедуры", answer)
        self.assertIn("соляная камера", answer)
        self.assertNotIn("недоступ", answer.lower())
        self.assertNotIn("Интердин", answer)
        self.assertNotIn("Электрокардиограмма", answer)

    def test_price_answers_do_not_expose_tariff_dates(self):
        answers = [
            self.kb.price_answer("Сколько стоит массаж головы?"),
            direct_answer("Сколько стоит путевка?"),
            direct_answer("Сколько стоит проживание?"),
        ]
        self.assertTrue(all("Прейскурант действует" not in answer for answer in answers))

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

    def test_package_followup_uses_conversation_history(self):
        history = [
            {"role": "user", "content": "Сколько стоит путевка на 5 дней?"},
            {"role": "assistant", "content": "Для одного человека путёвка стоит 25 500 ₽."},
        ]
        answer = direct_answer("2 клиента", history)
        self.assertIn("51 000 ₽", answer)
        self.assertIn("5 дней × 2 человека × 5 100 ₽", answer)

    def test_package_followup_understands_words(self):
        history = [{"role": "user", "content": "Путевка на 7 дней"}]
        answer = direct_answer("Нас трое", history)
        self.assertIn("107 100 ₽", answer)

    def test_package_for_three_people_without_days(self):
        answer = direct_answer("Сколько стоит путевка на трех человек?")
        self.assertIn("15 300 ₽ за один день", answer)
        self.assertIn("Скажите количество дней", answer)

    def test_people_followup_after_package_without_days(self):
        history = [
            {"role": "user", "content": "Сколько стоит путевка?"},
            {"role": "assistant", "content": "Путёвка стоит 5 100 ₽ за койко-день."},
        ]
        answer = direct_answer("Нас 2 человека", history)
        self.assertIn("10 200 ₽ за один день", answer)

    def test_people_and_days_in_one_question(self):
        answer = direct_answer("Сколько стоит путевка на трех человек на 5 дней?")
        self.assertIn("76 500 ₽", answer)

    def test_people_without_package_context_does_not_invent_calculation(self):
        self.assertIsNone(direct_answer("2 клиента", []))

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
