import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.cwd();
const SKILL_DIR = "C:/Users/denis/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const TMP_DIR = path.join(workspaceDir, ".pptx-build");
const FINAL_PPTX = path.join(workspaceDir, "final_project/presentation/Итоговый_проект_Лукоморье.pptx");
const RUNTIME_PYTHON = "C:/Users/denis/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const { resolvePresentationFont, applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);
await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const font = resolvePresentationFont();
const pres = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { ink: "#17352E", green: "#1B6B58", mint: "#DCEFE9", cream: "#F7F3E8", gold: "#E4B34D", white: "#FFFFFF", gray: "#52645E", red: "#A4483D" };

function box(slide, x, y, w, h, fill, radius = 12) {
  return slide.shapes.add({ geometry: "roundRect", position: { left: x, top: y, width: w, height: h }, fill, line: { fill: "none", width: 0 }, cornerRadius: radius });
}
function text(slide, value, x, y, w, h, size = 26, color = C.ink, bold = false, align = "left") {
  const s = slide.shapes.add({ geometry: "textbox", position: { left: x, top: y, width: w, height: h }, fill: "none", line: { fill: "none", width: 0 } });
  s.text = value;
  s.text.style = { typeface: font, fontSize: size, color, bold, alignment: align, verticalAlignment: "middle", autoFit: "shrinkText" };
  return s;
}
function base(title, number) {
  const s = pres.slides.add();
  s.background.fill = C.cream;
  text(s, title, 64, 36, 1080, 66, 34, C.ink, true);
  text(s, String(number).padStart(2, "0"), 1160, 42, 56, 44, 18, C.green, true, "right");
  return s;
}
function pill(slide, value, x, y, w, fill = C.mint) {
  box(slide, x, y, w, 42, fill);
  text(slide, value, x + 12, y + 3, w - 24, 36, 17, C.ink, true, "center");
}

// 1 — cover
{
  const s = pres.slides.add();
  s.background.fill = C.green;
  text(s, "AI-АССИСТЕНТ\n«ЛУКОМОРЬЕ»", 72, 105, 780, 180, 55, C.white, true);
  text(s, "Кодовый RAG-сервис для сайта санатория-профилактория", 78, 308, 690, 74, 26, C.white);
  box(s, 865, 100, 300, 420, C.cream);
  text(s, "18", 900, 142, 230, 100, 76, C.green, true, "center");
  text(s, "документов\nв базе знаний", 900, 238, 230, 80, 24, C.ink, true, "center");
  text(s, "RAG  •  кеш  •  веб-чат\nOpenAI Responses API", 900, 360, 230, 86, 20, C.gray, false, "center");
  text(s, "Итоговый проект курса • 2026", 78, 622, 540, 38, 18, C.white);
  s.speakerNotes.textFrame.setText("Проект создан на основе официального сайта https://aolukomorie56.ru/ и приложенных прейскурантов.");
}

// 2 — problem
{
  const s = base("Проблема: информация есть, но она распределена", 2);
  const items = [
    ["Повторяющиеся вопросы", "Цены, процедуры, документы и правила заезда"],
    ["Риск ошибки", "Тарифы меняются, медицинские ответы требуют осторожности"],
    ["Ограниченное время", "Администратор не может отвечать круглосуточно"],
  ];
  items.forEach((it, i) => {
    const y = 145 + i * 150;
    box(s, 70, y, 1080, 112, i === 1 ? "#F6E4DE" : C.white);
    text(s, String(i + 1), 92, y + 22, 58, 58, 34, i === 1 ? C.red : C.green, true, "center");
    text(s, it[0], 175, y + 17, 360, 38, 25, C.ink, true);
    text(s, it[1], 175, y + 55, 900, 38, 20, C.gray);
  });
  text(s, "Цель: дать быстрый проверяемый ответ и не подменять врача или администратора.", 72, 620, 1070, 38, 22, C.green, true);
  s.speakerNotes.textFrame.setText("Источник проблемы и сценариев: техническое задание проекта; официальный сайт https://aolukomorie56.ru/.");
}

// 3 — solution
{
  const s = base("Решение: веб-ассистент со строгим RAG", 3);
  const steps = [
    ["1", "Вопрос", "Виджет на сайте"],
    ["2", "Поиск", "Лексика + embeddings"],
    ["3", "Контекст", "Только релевантные факты"],
    ["4", "Ответ", "OpenAI + источники"],
  ];
  steps.forEach((it, i) => {
    const x = 65 + i * 296;
    box(s, x, 176, 250, 220, i === 3 ? C.green : C.white);
    text(s, it[0], x + 18, 192, 44, 44, 24, i === 3 ? C.white : C.green, true, "center");
    text(s, it[1], x + 24, 258, 202, 45, 27, i === 3 ? C.white : C.ink, true, "center");
    text(s, it[2], x + 24, 314, 202, 58, 18, i === 3 ? C.white : C.gray, false, "center");
    if (i < 3) text(s, "→", x + 252, 254, 42, 42, 30, C.gold, true, "center");
  });
  pill(s, "SQLite-кеш", 180, 465, 210);
  pill(s, "store: false", 420, 465, 210);
  pill(s, "CORS + rate limit", 660, 465, 250);
  pill(s, "без текста в логах", 940, 465, 240);
  text(s, "Если факта нет — честный отказ и телефоны администратора.", 170, 565, 940, 55, 28, C.green, true, "center");
  s.speakerNotes.textFrame.setText("Архитектура: код проекта; OpenAI Responses API https://platform.openai.com/docs/api-reference/responses.");
}

// 4 — KB
{
  const s = base("База знаний: 18 документов с приоритетом источников", 4);
  const cols = [
    ["Действующие прайсы", "Путёвки 2026\n98 медицинских услуг"],
    ["Официальный сайт", "Размещение, правила,\nдокументы, контакты"],
    ["Процедуры", "Что это, показания,\nпротивопоказания"],
  ];
  cols.forEach((it, i) => {
    const x = 75 + i * 390;
    box(s, x, 155, 350, 245, i === 0 ? C.green : C.white);
    text(s, it[0], x + 28, 190, 294, 58, 27, i === 0 ? C.white : C.ink, true, "center");
    text(s, it[1], x + 30, 265, 290, 90, 21, i === 0 ? C.white : C.gray, false, "center");
  });
  text(s, "Не включено", 80, 464, 205, 42, 22, C.red, true);
  text(s, "новости • акции • отзывы • неподтверждённые обещания", 290, 464, 850, 42, 23, C.ink);
  text(s, "Актуализация: новый прайс → версия базы → переиндексация → тесты", 80, 555, 1080, 52, 25, C.green, true);
  s.speakerNotes.textFrame.setText("Источники: https://aolukomorie56.ru/; https://aolukomorie56.ru/pravila/; https://aolukomorie56.ru/dostupnaya-sreda/; приложенные XLS-прейскуранты.");
}

// 5 — demo
{
  const s = base("Демо: типовой диалог и безопасные границы", 5);
  box(s, 70, 135, 750, 470, C.white);
  pill(s, "Клиент", 100, 165, 120, "#E6E9E8");
  text(s, "Сколько стоит отдых с лечением\nи питанием на 5 дней?", 105, 215, 650, 70, 25, C.ink, true);
  pill(s, "ИИ", 100, 310, 80, C.mint);
  text(s, "25 500 ₽ на одного человека\n5 × 5 100 ₽\n\nВ тариф входят проживание, трёхразовое питание\nи лечение по назначению врача.", 105, 356, 650, 174, 22, C.green, false);
  box(s, 870, 135, 330, 215, C.green);
  text(s, "5 типовых", 910, 174, 250, 52, 34, C.white, true, "center");
  text(s, "цены • процедуры\nдокументы • программа", 910, 235, 250, 72, 19, C.white, false, "center");
  box(s, 870, 380, 330, 225, "#F4E4DE");
  text(s, "2 вне темы", 910, 420, 250, 52, 34, C.red, true, "center");
  text(s, "без выдумки:\nотказ + контакты", 910, 485, 250, 72, 20, C.ink, false, "center");
  s.speakerNotes.textFrame.setText("Демо: https://bot.aolukomorie56.ru/demo. Тариф: официальный прайс 2026 https://aolukomorie56.ru/wp-content/uploads/2026/01/prajs-putevki-2026-god.pdf.");
}

// 6 — economics
{
  const s = base("Экономика: первый год — около $1.65 тыс.", 6);
  const chart = s.charts.add("bar", {
    position: { left: 70, top: 150, width: 720, height: 420 },
    categories: ["Разработка", "OpenAI API", "VPS", "Мониторинг", "Сопровождение", "Резерв"],
    series: [{ name: "USD", values: [600, 273.77, 180, 60, 360, 174.75], fill: C.green }],
    barOptions: { direction: "column", grouping: "clustered" },
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
  });
  applyPresentationChartFont(chart, { fontFamily: font });
  box(s, 850, 150, 350, 180, C.green);
  text(s, "$1 648.52", 875, 185, 300, 70, 44, C.white, true, "center");
  text(s, "первый год", 875, 260, 300, 40, 21, C.white, false, "center");
  box(s, 850, 360, 350, 210, C.white);
  text(s, "≈ 639 часов", 875, 395, 300, 55, 34, C.green, true, "center");
  text(s, "потенциальная экономия\nвремени администратора в год", 885, 462, 280, 72, 19, C.gray, false, "center");
  text(s, "Допущения: 50 обращений/день, 4 000 токенов/ответ, 70% автоматизации.", 75, 607, 1070, 34, 17, C.gray);
  s.speakerNotes.textFrame.setText("Тарифы: https://developers.openai.com/api/docs/models/gpt-5.6-terra и https://developers.openai.com/api/docs/models/text-embedding-3-small. Все показатели — расчётные допущения, не гарантия.");
}

// 7 — result and roadmap
{
  const s = base("Результат и следующий шаг", 7);
  const metrics = [["≥90%", "точность тестов"], ["<30 с", "ответ MVP"], ["24/7", "доступ через сайт"]];
  metrics.forEach((it, i) => {
    const x = 75 + i * 390;
    box(s, x, 145, 350, 155, i === 0 ? C.green : C.white);
    text(s, it[0], x + 20, 170, 310, 58, 42, i === 0 ? C.white : C.green, true, "center");
    text(s, it[1], x + 20, 235, 310, 36, 19, i === 0 ? C.white : C.gray, false, "center");
  });
  text(s, "Дальше", 75, 365, 200, 46, 26, C.ink, true);
  const roadmap = ["редактор и версии базы", "аналитика неотвеченных вопросов", "контроль изменения прайсов", "интеграция бронирования после оценки ПДн"];
  roadmap.forEach((v, i) => {
    pill(s, `${i + 1}. ${v}`, 75 + (i % 2) * 555, 430 + Math.floor(i / 2) * 75, 520, i === 3 ? "#F4E4DE" : C.mint);
  });
  text(s, "Демо: bot.aolukomorie56.ru/demo", 75, 622, 790, 38, 24, C.green, true);
  text(s, "Спасибо!", 990, 622, 180, 38, 22, C.ink, true, "right");
  s.speakerNotes.textFrame.setText("Критерии и планы: Техническое задание проекта, версия 2.0 от 08.10.2026.");
}

const requirements = {
  explicitTotalSlideCount: 7,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [6],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const fontPolicy = { basis: "design", families: [font] };
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "lukomorie-candidate.pptx");
await (await PresentationFile.exportPptx(pres)).save(candidatePath);
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  requiredNativeChartOwnerSlides: [6],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "lukomorie.validation.json"),
});
console.log(JSON.stringify(result, null, 2));
