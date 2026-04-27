let tokenSequence = 0;
let promptWorkbenchInstanceSequence = 0;

const PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT = "rookieui:prompt-workbench-language-sync";

const WORKBENCH_I18N = Object.freeze({
  en: {
    title: "Prompt Workbench",
    subtitle: "Structured prompt editor with persisted history, favorites, formatting rules, and blacklist-aware cleanup.",
    openWorkbench: "Open Workbench",
    hideWorkbench: "Hide Workbench",
    promptTab: "Prompt",
    negativeTab: "Negative",
    summaryState: "State",
    summaryProviders: "Providers",
    summaryCatalogs: "Catalogs",
    summaryHistory: "History",
    summaryFavorites: "Favorites",
    summaryBlacklist: "Blacklist",
    panelEditor: "Editor",
    panelHistory: "History",
    panelFavorites: "Favorites",
    panelCatalog: "Catalog",
    panelAssist: "Assist",
    panelFormat: "Format",
    captureCurrentText: "Capture Current Text",
    restoreDraft: "Restore Draft",
    ready: "Prompt Workbench ready",
    formattingAndBlacklist: "Formatting and Blacklist",
    importExport: "Import / Export",
    exportJson: "Export JSON",
    importJson: "Import JSON",
    exportReady: "Prompt Workbench export JSON generated",
    importReady: "Prompt Workbench import synchronized",
    importInvalidJson: "Import JSON must be a valid object",
    foldTools: "Fold tools",
    openTools: "Open tools",
    promptTokenCount: "Prompt token count",
    languageAndScope: "Prompt workbench language and scope",
    languageSelector: "Prompt Workbench language selector",
    promptScope: "prompt",
    negativeScope: "negative",
    tagSingular: "tag",
    tagPlural: "tags",
    enterNewKeyword: "Enter new keyword",
    keywordInput: "Prompt Workbench keyword input",
    enterToAddKeyword: "Enter to add keyword",
    preferencesShort: "Prefs",
    preferences: "Preferences",
    append: "Append",
    noInlineSuggestions: "No inline suggestions loaded yet.",
    groupTags: "Group Tags",
    showGroupTags: "Show Group Tags",
    hideGroupTags: "Hide Group Tags",
    groupTagsHidden: "Group Tags are hidden.",
    noGroupTags: "No group tags are loaded yet.",
    groupTagInserted: "Inserted {label}",
    groupTagRemoved: "Removed {label}",
    historyLoaded: "Prompt Workbench history loaded",
    favoritesLoaded: "Prompt Workbench favorites loaded",
    appendLoaded: "Prompt Workbench append dropdown loaded",
    copiedActivePrompt: "Copied active prompt text",
    clearedActivePrompt: "Cleared active prompt text",
    editorPrompt: "Prompt Editor",
    editorNegative: "Negative Prompt Editor",
    savedDraft: "Saved draft: {count} prompt units",
    activePanel: "Active panel: {panel}",
    scopeDetail: "{scope} namespace: {namespace}",
    promptNamespace: "Prompt",
    negativeNamespace: "Negative Prompt",
    persistedOpen: "Persisted open",
    collapsed: "Collapsed",
    lazy: "Lazy",
    entries: "entries",
    disabled: "Disabled",
    blocked: "blocked",
    groupsCount: "groups",
    sectionsCount: "sections",
    networksCount: "networks",
    translateProviders: "translate",
    assistProviders: "assist",
  },
  "zh-TW": {
    title: "提示詞工作台",
    subtitle: "結構化提示詞編輯器，支援歷史、收藏、格式化規則與黑名單清理。",
    openWorkbench: "開啟工作台",
    hideWorkbench: "收合工作台",
    promptTab: "正向提示詞",
    negativeTab: "反向提示詞",
    summaryState: "狀態",
    summaryProviders: "供應器",
    summaryCatalogs: "目錄",
    summaryHistory: "歷史",
    summaryFavorites: "收藏",
    summaryBlacklist: "黑名單",
    panelEditor: "編輯",
    panelHistory: "歷史",
    panelFavorites: "收藏",
    panelCatalog: "目錄",
    panelAssist: "助理",
    panelFormat: "格式",
    captureCurrentText: "擷取目前文字",
    restoreDraft: "還原草稿",
    ready: "提示詞工作台已就緒",
    formattingAndBlacklist: "格式化與黑名單",
    importExport: "匯入 / 匯出",
    exportJson: "匯出 JSON",
    importJson: "匯入 JSON",
    exportReady: "提示詞工作台匯出 JSON 已產生",
    importReady: "提示詞工作台匯入已同步",
    importInvalidJson: "匯入 JSON 必須是有效物件",
    foldTools: "收合工具",
    openTools: "開啟工具",
    promptTokenCount: "提示詞標籤數",
    languageAndScope: "提示詞工作台語系與範圍",
    languageSelector: "提示詞工作台語系選單",
    promptScope: "正向",
    negativeScope: "反向",
    tagSingular: "標籤",
    tagPlural: "標籤",
    enterNewKeyword: "請輸入新關鍵詞",
    keywordInput: "提示詞工作台關鍵詞輸入",
    enterToAddKeyword: "按 Enter 加入關鍵詞",
    preferencesShort: "偏好",
    preferences: "偏好設定",
    append: "加入",
    noInlineSuggestions: "尚未載入即時建議。",
    groupTags: "分組標籤",
    showGroupTags: "顯示分組標籤",
    hideGroupTags: "隱藏分組標籤",
    groupTagsHidden: "分組標籤已隱藏。",
    noGroupTags: "尚未載入分組標籤。",
    groupTagInserted: "已加入 {label}",
    groupTagRemoved: "已移除 {label}",
    historyLoaded: "提示詞工作台歷史已載入",
    favoritesLoaded: "提示詞工作台收藏已載入",
    appendLoaded: "提示詞工作台加入選單已載入",
    copiedActivePrompt: "已複製目前提示詞",
    clearedActivePrompt: "已清除目前提示詞",
    editorPrompt: "正向提示詞編輯器",
    editorNegative: "反向提示詞編輯器",
    savedDraft: "已儲存草稿：{count} 個提示詞單位",
    activePanel: "目前面板：{panel}",
    scopeDetail: "{scope} 命名空間：{namespace}",
    promptNamespace: "正向提示詞",
    negativeNamespace: "反向提示詞",
    persistedOpen: "已記住開啟",
    collapsed: "已收合",
    lazy: "延遲載入",
    entries: "筆",
    disabled: "停用",
    blocked: "封鎖",
    groupsCount: "組",
    sectionsCount: "段",
    networksCount: "網路",
    translateProviders: "翻譯",
    assistProviders: "助理",
  },
  "zh-CN": {
    title: "提示词工作台",
    subtitle: "结构化提示词编辑器，支持历史、收藏、格式化规则与黑名单清理。",
    openWorkbench: "打开工作台",
    hideWorkbench: "收起工作台",
    promptTab: "正向提示词",
    negativeTab: "反向提示词",
    panelEditor: "编辑",
    panelHistory: "历史",
    panelFavorites: "收藏",
    panelCatalog: "目录",
    panelAssist: "助手",
    panelFormat: "格式",
    foldTools: "收起工具",
    openTools: "打开工具",
    promptTokenCount: "提示词标签数",
    languageAndScope: "提示词工作台语言和范围",
    languageSelector: "提示词工作台语言菜单",
    promptScope: "正向",
    negativeScope: "反向",
    tagSingular: "标签",
    tagPlural: "标签",
    enterNewKeyword: "请输入新关键词",
    keywordInput: "提示词工作台关键词输入",
    enterToAddKeyword: "按 Enter 添加关键词",
    preferencesShort: "偏好",
    preferences: "偏好设置",
    append: "加入",
    noInlineSuggestions: "尚未加载即时建议。",
    groupTags: "分组标签",
    showGroupTags: "显示分组标签",
    hideGroupTags: "隐藏分组标签",
    groupTagsHidden: "分组标签已隐藏。",
    noGroupTags: "尚未加载分组标签。",
  },
  ja: {
    title: "プロンプトワークベンチ",
    subtitle: "履歴、お気に入り、整形ルール、ブラックリスト整理に対応した構造化プロンプトエディター。",
    openWorkbench: "ワークベンチを開く",
    hideWorkbench: "ワークベンチを隠す",
    promptTab: "プロンプト",
    negativeTab: "ネガティブ",
    panelEditor: "編集",
    panelHistory: "履歴",
    panelFavorites: "お気に入り",
    panelCatalog: "カタログ",
    panelAssist: "アシスト",
    panelFormat: "整形",
    foldTools: "ツールを折りたたむ",
    openTools: "ツールを開く",
    promptTokenCount: "プロンプトタグ数",
    languageAndScope: "プロンプトワークベンチの言語と範囲",
    languageSelector: "プロンプトワークベンチ言語メニュー",
    promptScope: "プロンプト",
    negativeScope: "ネガティブ",
    tagSingular: "タグ",
    tagPlural: "タグ",
    enterNewKeyword: "新しいキーワードを入力",
    keywordInput: "プロンプトワークベンチのキーワード入力",
    enterToAddKeyword: "Enter でキーワードを追加",
    preferencesShort: "設定",
    preferences: "環境設定",
    append: "追加",
    noInlineSuggestions: "インライン候補はまだ読み込まれていません。",
    groupTags: "グループタグ",
    showGroupTags: "グループタグを表示",
    hideGroupTags: "グループタグを隠す",
    groupTagsHidden: "グループタグは非表示です。",
    noGroupTags: "グループタグはまだ読み込まれていません。",
  },
  ko: {
    title: "프롬프트 워크벤치",
    subtitle: "기록, 즐겨찾기, 서식 규칙, 블랙리스트 정리를 지원하는 구조화된 프롬프트 편집기.",
    openWorkbench: "워크벤치 열기",
    hideWorkbench: "워크벤치 숨기기",
    promptTab: "프롬프트",
    negativeTab: "네거티브",
    panelEditor: "편집",
    panelHistory: "기록",
    panelFavorites: "즐겨찾기",
    panelCatalog: "카탈로그",
    panelAssist: "지원",
    panelFormat: "서식",
    foldTools: "도구 접기",
    openTools: "도구 열기",
    promptTokenCount: "프롬프트 태그 수",
    languageAndScope: "프롬프트 워크벤치 언어와 범위",
    languageSelector: "프롬프트 워크벤치 언어 메뉴",
    promptScope: "프롬프트",
    negativeScope: "네거티브",
    tagSingular: "태그",
    tagPlural: "태그",
    enterNewKeyword: "새 키워드 입력",
    keywordInput: "프롬프트 워크벤치 키워드 입력",
    enterToAddKeyword: "Enter로 키워드 추가",
    preferencesShort: "설정",
    preferences: "환경 설정",
    append: "추가",
    noInlineSuggestions: "인라인 제안이 아직 로드되지 않았습니다.",
    groupTags: "그룹 태그",
    showGroupTags: "그룹 태그 표시",
    hideGroupTags: "그룹 태그 숨기기",
    groupTagsHidden: "그룹 태그가 숨겨져 있습니다.",
    noGroupTags: "그룹 태그가 아직 로드되지 않았습니다.",
  },
  ar: {
    title: "منضدة الموجهات",
    subtitle: "محرر موجهات منظم يدعم السجل والمفضلات وقواعد التنسيق وتنظيف القائمة السوداء.",
    openWorkbench: "فتح المنضدة",
    hideWorkbench: "إخفاء المنضدة",
    promptTab: "الموجه",
    negativeTab: "الموجه السلبي",
    panelEditor: "المحرر",
    panelHistory: "السجل",
    panelFavorites: "المفضلات",
    panelCatalog: "الفهرس",
    panelAssist: "المساعدة",
    panelFormat: "التنسيق",
    foldTools: "طي الأدوات",
    openTools: "فتح الأدوات",
    promptTokenCount: "عدد وسوم الموجه",
    languageAndScope: "لغة ونطاق منضدة الموجهات",
    languageSelector: "قائمة لغة منضدة الموجهات",
    promptScope: "الموجه",
    negativeScope: "السلبي",
    tagSingular: "وسم",
    tagPlural: "وسوم",
    enterNewKeyword: "أدخل كلمة مفتاحية جديدة",
    keywordInput: "إدخال كلمة مفتاحية لمنضدة الموجهات",
    enterToAddKeyword: "اضغط Enter لإضافة كلمة مفتاحية",
    preferencesShort: "تفضيلات",
    preferences: "التفضيلات",
    append: "إضافة",
    noInlineSuggestions: "لم يتم تحميل اقتراحات فورية بعد.",
    groupTags: "وسوم المجموعات",
    showGroupTags: "إظهار وسوم المجموعات",
    hideGroupTags: "إخفاء وسوم المجموعات",
    groupTagsHidden: "وسوم المجموعات مخفية.",
    noGroupTags: "لم يتم تحميل وسوم مجموعات بعد.",
  },
  es: {
    title: "Banco de prompts",
    subtitle: "Editor de prompts estructurado con historial, favoritos, reglas de formato y limpieza con lista negra.",
    openWorkbench: "Abrir banco",
    hideWorkbench: "Ocultar banco",
    promptTab: "Prompt",
    negativeTab: "Negativo",
    panelEditor: "Editor",
    panelHistory: "Historial",
    panelFavorites: "Favoritos",
    panelCatalog: "Catálogo",
    panelAssist: "Asistente",
    panelFormat: "Formato",
    foldTools: "Plegar herramientas",
    openTools: "Abrir herramientas",
    promptTokenCount: "Recuento de etiquetas",
    languageAndScope: "Idioma y alcance del banco de prompts",
    languageSelector: "Selector de idioma del banco de prompts",
    promptScope: "prompt",
    negativeScope: "negativo",
    tagSingular: "etiqueta",
    tagPlural: "etiquetas",
    enterNewKeyword: "Introduce una nueva palabra clave",
    keywordInput: "Entrada de palabra clave del banco de prompts",
    enterToAddKeyword: "Pulsa Enter para añadir palabra clave",
    preferencesShort: "Prefs",
    preferences: "Preferencias",
    append: "Añadir",
    noInlineSuggestions: "Aún no se han cargado sugerencias en línea.",
    groupTags: "Etiquetas por grupo",
    showGroupTags: "Mostrar etiquetas por grupo",
    hideGroupTags: "Ocultar etiquetas por grupo",
    groupTagsHidden: "Las etiquetas por grupo están ocultas.",
    noGroupTags: "Aún no se han cargado etiquetas por grupo.",
  },
  fa: {
    title: "میزکار پرامپت",
    subtitle: "ویرایشگر ساختاریافته پرامپت با تاریخچه، علاقه مندی ها، قواعد قالب بندی و پاکسازی فهرست سیاه.",
    openWorkbench: "باز کردن میزکار",
    hideWorkbench: "پنهان کردن میزکار",
    promptTab: "پرامپت",
    negativeTab: "پرامپت منفی",
    panelEditor: "ویرایشگر",
    panelHistory: "تاریخچه",
    panelFavorites: "علاقه مندی ها",
    panelCatalog: "فهرست",
    panelAssist: "دستیار",
    panelFormat: "قالب بندی",
    foldTools: "جمع کردن ابزارها",
    openTools: "باز کردن ابزارها",
    promptTokenCount: "شمار برچسب های پرامپت",
    languageAndScope: "زبان و محدوده میزکار پرامپت",
    languageSelector: "منوی زبان میزکار پرامپت",
    promptScope: "پرامپت",
    negativeScope: "منفی",
    tagSingular: "برچسب",
    tagPlural: "برچسب",
    enterNewKeyword: "کلیدواژه جدید را وارد کنید",
    keywordInput: "ورودی کلیدواژه میزکار پرامپت",
    enterToAddKeyword: "برای افزودن کلیدواژه Enter را فشار دهید",
    preferencesShort: "ترجیحات",
    preferences: "ترجیحات",
    append: "افزودن",
    noInlineSuggestions: "هنوز پیشنهاد درون خطی بارگیری نشده است.",
    groupTags: "برچسب های گروهی",
    showGroupTags: "نمایش برچسب های گروهی",
    hideGroupTags: "پنهان کردن برچسب های گروهی",
    groupTagsHidden: "برچسب های گروهی پنهان هستند.",
    noGroupTags: "هنوز برچسب گروهی بارگیری نشده است.",
  },
  fr: {
    title: "Atelier de prompts",
    subtitle: "Éditeur de prompts structuré avec historique, favoris, règles de formatage et nettoyage par liste noire.",
    openWorkbench: "Ouvrir l'atelier",
    hideWorkbench: "Masquer l'atelier",
    promptTab: "Prompt",
    negativeTab: "Négatif",
    panelEditor: "Éditeur",
    panelHistory: "Historique",
    panelFavorites: "Favoris",
    panelCatalog: "Catalogue",
    panelAssist: "Assistant",
    panelFormat: "Format",
    foldTools: "Replier les outils",
    openTools: "Ouvrir les outils",
    promptTokenCount: "Nombre d'étiquettes",
    languageAndScope: "Langue et portée de l'atelier de prompts",
    languageSelector: "Sélecteur de langue de l'atelier de prompts",
    promptScope: "prompt",
    negativeScope: "négatif",
    tagSingular: "étiquette",
    tagPlural: "étiquettes",
    enterNewKeyword: "Saisir un nouveau mot-clé",
    keywordInput: "Saisie de mot-clé de l'atelier de prompts",
    enterToAddKeyword: "Appuyez sur Entrée pour ajouter le mot-clé",
    preferencesShort: "Prefs",
    preferences: "Préférences",
    append: "Ajouter",
    noInlineSuggestions: "Aucune suggestion en ligne chargée pour le moment.",
    groupTags: "Étiquettes groupées",
    showGroupTags: "Afficher les étiquettes groupées",
    hideGroupTags: "Masquer les étiquettes groupées",
    groupTagsHidden: "Les étiquettes groupées sont masquées.",
    noGroupTags: "Aucune étiquette groupée n'est encore chargée.",
  },
  ru: {
    title: "Рабочая область промптов",
    subtitle: "Структурированный редактор промптов с историей, избранным, правилами форматирования и очисткой по черному списку.",
    openWorkbench: "Открыть область",
    hideWorkbench: "Скрыть область",
    promptTab: "Промпт",
    negativeTab: "Негатив",
    panelEditor: "Редактор",
    panelHistory: "История",
    panelFavorites: "Избранное",
    panelCatalog: "Каталог",
    panelAssist: "Помощь",
    panelFormat: "Формат",
    foldTools: "Свернуть инструменты",
    openTools: "Открыть инструменты",
    promptTokenCount: "Количество тегов промпта",
    languageAndScope: "Язык и область рабочего пространства промптов",
    languageSelector: "Меню языка рабочего пространства промптов",
    promptScope: "промпт",
    negativeScope: "негатив",
    tagSingular: "тег",
    tagPlural: "теги",
    enterNewKeyword: "Введите новое ключевое слово",
    keywordInput: "Ввод ключевого слова для рабочего пространства промптов",
    enterToAddKeyword: "Нажмите Enter, чтобы добавить ключевое слово",
    preferencesShort: "Настр.",
    preferences: "Настройки",
    append: "Добавить",
    noInlineSuggestions: "Встроенные предложения еще не загружены.",
    groupTags: "Групповые теги",
    showGroupTags: "Показать групповые теги",
    hideGroupTags: "Скрыть групповые теги",
    groupTagsHidden: "Групповые теги скрыты.",
    noGroupTags: "Групповые теги еще не загружены.",
  },
  tr: {
    title: "Prompt Tezgahı",
    subtitle: "Geçmiş, favoriler, biçimlendirme kuralları ve kara liste temizliği olan yapılandırılmış prompt düzenleyici.",
    openWorkbench: "Tezgahı aç",
    hideWorkbench: "Tezgahı gizle",
    promptTab: "Prompt",
    negativeTab: "Negatif",
    panelEditor: "Düzenleyici",
    panelHistory: "Geçmiş",
    panelFavorites: "Favoriler",
    panelCatalog: "Katalog",
    panelAssist: "Yardım",
    panelFormat: "Biçim",
    foldTools: "Araçları daralt",
    openTools: "Araçları aç",
    promptTokenCount: "Prompt etiket sayısı",
    languageAndScope: "Prompt tezgahı dili ve kapsamı",
    languageSelector: "Prompt tezgahı dil menüsü",
    promptScope: "prompt",
    negativeScope: "negatif",
    tagSingular: "etiket",
    tagPlural: "etiket",
    enterNewKeyword: "Yeni anahtar kelime gir",
    keywordInput: "Prompt tezgahı anahtar kelime girişi",
    enterToAddKeyword: "Anahtar kelime eklemek için Enter'a bas",
    preferencesShort: "Tercih",
    preferences: "Tercihler",
    append: "Ekle",
    noInlineSuggestions: "Henüz satır içi öneri yüklenmedi.",
    groupTags: "Grup Etiketleri",
    showGroupTags: "Grup etiketlerini göster",
    hideGroupTags: "Grup etiketlerini gizle",
    groupTagsHidden: "Grup etiketleri gizli.",
    noGroupTags: "Henüz grup etiketi yüklenmedi.",
  },
  "pt-BR": {
    title: "Bancada de prompts",
    subtitle: "Editor de prompts estruturado com histórico, favoritos, regras de formatação e limpeza por lista negra.",
    openWorkbench: "Abrir bancada",
    hideWorkbench: "Ocultar bancada",
    promptTab: "Prompt",
    negativeTab: "Negativo",
    panelEditor: "Editor",
    panelHistory: "Histórico",
    panelFavorites: "Favoritos",
    panelCatalog: "Catálogo",
    panelAssist: "Assistente",
    panelFormat: "Formato",
    foldTools: "Recolher ferramentas",
    openTools: "Abrir ferramentas",
    promptTokenCount: "Contagem de tags",
    languageAndScope: "Idioma e escopo da bancada de prompts",
    languageSelector: "Seletor de idioma da bancada de prompts",
    promptScope: "prompt",
    negativeScope: "negativo",
    tagSingular: "tag",
    tagPlural: "tags",
    enterNewKeyword: "Insira nova palavra-chave",
    keywordInput: "Entrada de palavra-chave da bancada de prompts",
    enterToAddKeyword: "Pressione Enter para adicionar palavra-chave",
    preferencesShort: "Prefs",
    preferences: "Preferências",
    append: "Adicionar",
    noInlineSuggestions: "Nenhuma sugestão em linha carregada ainda.",
    groupTags: "Tags agrupadas",
    showGroupTags: "Mostrar tags agrupadas",
    hideGroupTags: "Ocultar tags agrupadas",
    groupTagsHidden: "As tags agrupadas estão ocultas.",
    noGroupTags: "Nenhuma tag agrupada foi carregada ainda.",
  },
  de: {
    title: "Prompt-Werkbank",
    subtitle: "Strukturierter Prompt-Editor mit Verlauf, Favoriten, Formatierungsregeln und Blacklist-Bereinigung.",
    openWorkbench: "Werkbank öffnen",
    hideWorkbench: "Werkbank ausblenden",
    promptTab: "Prompt",
    negativeTab: "Negativ",
    panelEditor: "Editor",
    panelHistory: "Verlauf",
    panelFavorites: "Favoriten",
    panelCatalog: "Katalog",
    panelAssist: "Assistenz",
    panelFormat: "Format",
    foldTools: "Werkzeuge einklappen",
    openTools: "Werkzeuge öffnen",
    promptTokenCount: "Prompt-Tag-Anzahl",
    languageAndScope: "Sprache und Bereich der Prompt-Werkbank",
    languageSelector: "Sprachauswahl der Prompt-Werkbank",
    promptScope: "Prompt",
    negativeScope: "Negativ",
    tagSingular: "Tag",
    tagPlural: "Tags",
    enterNewKeyword: "Neues Schlüsselwort eingeben",
    keywordInput: "Schlüsselworteingabe der Prompt-Werkbank",
    enterToAddKeyword: "Enter drücken, um Schlüsselwort hinzuzufügen",
    preferencesShort: "Prefs",
    preferences: "Einstellungen",
    append: "Hinzufügen",
    noInlineSuggestions: "Noch keine Inline-Vorschläge geladen.",
    groupTags: "Gruppen-Tags",
    showGroupTags: "Gruppen-Tags anzeigen",
    hideGroupTags: "Gruppen-Tags ausblenden",
    groupTagsHidden: "Gruppen-Tags sind ausgeblendet.",
    noGroupTags: "Noch keine Gruppen-Tags geladen.",
  },
  it: {
    title: "Banco prompt",
    subtitle: "Editor di prompt strutturato con cronologia, preferiti, regole di formattazione e pulizia tramite blacklist.",
    openWorkbench: "Apri banco",
    hideWorkbench: "Nascondi banco",
    promptTab: "Prompt",
    negativeTab: "Negativo",
    panelEditor: "Editor",
    panelHistory: "Cronologia",
    panelFavorites: "Preferiti",
    panelCatalog: "Catalogo",
    panelAssist: "Assistenza",
    panelFormat: "Formato",
    foldTools: "Comprimi strumenti",
    openTools: "Apri strumenti",
    promptTokenCount: "Conteggio tag prompt",
    languageAndScope: "Lingua e ambito del banco prompt",
    languageSelector: "Selettore lingua del banco prompt",
    promptScope: "prompt",
    negativeScope: "negativo",
    tagSingular: "tag",
    tagPlural: "tag",
    enterNewKeyword: "Inserisci nuova parola chiave",
    keywordInput: "Input parola chiave del banco prompt",
    enterToAddKeyword: "Premi Enter per aggiungere la parola chiave",
    preferencesShort: "Pref.",
    preferences: "Preferenze",
    append: "Aggiungi",
    noInlineSuggestions: "Nessun suggerimento inline ancora caricato.",
    groupTags: "Tag di gruppo",
    showGroupTags: "Mostra tag di gruppo",
    hideGroupTags: "Nascondi tag di gruppo",
    groupTagsHidden: "I tag di gruppo sono nascosti.",
    noGroupTags: "Nessun tag di gruppo ancora caricato.",
  },
  nl: {
    title: "Promptwerkbank",
    subtitle: "Gestructureerde prompteditor met geschiedenis, favorieten, opmaakregels en blacklist-opruiming.",
    openWorkbench: "Werkbank openen",
    hideWorkbench: "Werkbank verbergen",
    promptTab: "Prompt",
    negativeTab: "Negatief",
    panelEditor: "Editor",
    panelHistory: "Geschiedenis",
    panelFavorites: "Favorieten",
    panelCatalog: "Catalogus",
    panelAssist: "Assistent",
    panelFormat: "Opmaak",
    foldTools: "Gereedschap inklappen",
    openTools: "Gereedschap openen",
    promptTokenCount: "Aantal prompttags",
    languageAndScope: "Taal en bereik van promptwerkbank",
    languageSelector: "Taalkeuze van promptwerkbank",
    promptScope: "prompt",
    negativeScope: "negatief",
    tagSingular: "tag",
    tagPlural: "tags",
    enterNewKeyword: "Nieuwe sleutelterm invoeren",
    keywordInput: "Sleutelterminvoer van promptwerkbank",
    enterToAddKeyword: "Druk op Enter om sleutelterm toe te voegen",
    preferencesShort: "Prefs",
    preferences: "Voorkeuren",
    append: "Toevoegen",
    noInlineSuggestions: "Nog geen inline suggesties geladen.",
    groupTags: "Groepstags",
    showGroupTags: "Groepstags tonen",
    hideGroupTags: "Groepstags verbergen",
    groupTagsHidden: "Groepstags zijn verborgen.",
    noGroupTags: "Nog geen groepstags geladen.",
  },
  pl: {
    title: "Warsztat promptów",
    subtitle: "Strukturalny edytor promptów z historią, ulubionymi, regułami formatowania i czyszczeniem blacklisty.",
    openWorkbench: "Otwórz warsztat",
    hideWorkbench: "Ukryj warsztat",
    promptTab: "Prompt",
    negativeTab: "Negatyw",
    panelEditor: "Edytor",
    panelHistory: "Historia",
    panelFavorites: "Ulubione",
    panelCatalog: "Katalog",
    panelAssist: "Asysta",
    panelFormat: "Format",
    foldTools: "Zwiń narzędzia",
    openTools: "Otwórz narzędzia",
    promptTokenCount: "Liczba tagów promptu",
    languageAndScope: "Język i zakres warsztatu promptów",
    languageSelector: "Menu języka warsztatu promptów",
    promptScope: "prompt",
    negativeScope: "negatyw",
    tagSingular: "tag",
    tagPlural: "tagi",
    enterNewKeyword: "Wpisz nowe słowo kluczowe",
    keywordInput: "Pole słowa kluczowego warsztatu promptów",
    enterToAddKeyword: "Naciśnij Enter, aby dodać słowo kluczowe",
    preferencesShort: "Pref.",
    preferences: "Preferencje",
    append: "Dodaj",
    noInlineSuggestions: "Nie załadowano jeszcze sugestii inline.",
    groupTags: "Tagi grupowe",
    showGroupTags: "Pokaż tagi grupowe",
    hideGroupTags: "Ukryj tagi grupowe",
    groupTagsHidden: "Tagi grupowe są ukryte.",
    noGroupTags: "Nie załadowano jeszcze tagów grupowych.",
  },
  uk: {
    title: "Майстерня промптів",
    subtitle: "Структурований редактор промптів з історією, обраним, правилами форматування та очищенням за чорним списком.",
    openWorkbench: "Відкрити майстерню",
    hideWorkbench: "Приховати майстерню",
    promptTab: "Промпт",
    negativeTab: "Негатив",
    panelEditor: "Редактор",
    panelHistory: "Історія",
    panelFavorites: "Обране",
    panelCatalog: "Каталог",
    panelAssist: "Допомога",
    panelFormat: "Формат",
    foldTools: "Згорнути інструменти",
    openTools: "Відкрити інструменти",
    promptTokenCount: "Кількість тегів промпта",
    languageAndScope: "Мова і область майстерні промптів",
    languageSelector: "Меню мови майстерні промптів",
    promptScope: "промпт",
    negativeScope: "негатив",
    tagSingular: "тег",
    tagPlural: "теги",
    enterNewKeyword: "Введіть нове ключове слово",
    keywordInput: "Ввід ключового слова майстерні промптів",
    enterToAddKeyword: "Натисніть Enter, щоб додати ключове слово",
    preferencesShort: "Налашт.",
    preferences: "Налаштування",
    append: "Додати",
    noInlineSuggestions: "Вбудовані підказки ще не завантажені.",
    groupTags: "Групові теги",
    showGroupTags: "Показати групові теги",
    hideGroupTags: "Приховати групові теги",
    groupTagsHidden: "Групові теги приховані.",
    noGroupTags: "Групові теги ще не завантажені.",
  },
  vi: {
    title: "Bàn làm việc prompt",
    subtitle: "Trình chỉnh sửa prompt có cấu trúc với lịch sử, yêu thích, quy tắc định dạng và dọn dẹp danh sách đen.",
    openWorkbench: "Mở bàn làm việc",
    hideWorkbench: "Ẩn bàn làm việc",
    promptTab: "Prompt",
    negativeTab: "Negative",
    panelEditor: "Trình sửa",
    panelHistory: "Lịch sử",
    panelFavorites: "Yêu thích",
    panelCatalog: "Danh mục",
    panelAssist: "Hỗ trợ",
    panelFormat: "Định dạng",
    foldTools: "Thu gọn công cụ",
    openTools: "Mở công cụ",
    promptTokenCount: "Số thẻ prompt",
    languageAndScope: "Ngôn ngữ và phạm vi bàn làm việc prompt",
    languageSelector: "Menu ngôn ngữ bàn làm việc prompt",
    promptScope: "prompt",
    negativeScope: "negative",
    tagSingular: "thẻ",
    tagPlural: "thẻ",
    enterNewKeyword: "Nhập từ khóa mới",
    keywordInput: "Ô nhập từ khóa của bàn làm việc prompt",
    enterToAddKeyword: "Nhấn Enter để thêm từ khóa",
    preferencesShort: "Tùy chọn",
    preferences: "Tùy chọn",
    append: "Thêm",
    noInlineSuggestions: "Chưa tải gợi ý nội tuyến.",
    groupTags: "Thẻ nhóm",
    showGroupTags: "Hiển thị thẻ nhóm",
    hideGroupTags: "Ẩn thẻ nhóm",
    groupTagsHidden: "Thẻ nhóm đang bị ẩn.",
    noGroupTags: "Chưa tải thẻ nhóm.",
  },
  th: {
    title: "เวิร์กเบนช์พรอมป์",
    subtitle: "ตัวแก้ไขพรอมป์แบบมีโครงสร้าง พร้อมประวัติ รายการโปรด กฎรูปแบบ และการล้างบัญชีดำ.",
    openWorkbench: "เปิดเวิร์กเบนช์",
    hideWorkbench: "ซ่อนเวิร์กเบนช์",
    promptTab: "พรอมป์",
    negativeTab: "เนกาทีฟ",
    panelEditor: "ตัวแก้ไข",
    panelHistory: "ประวัติ",
    panelFavorites: "รายการโปรด",
    panelCatalog: "แค็ตตาล็อก",
    panelAssist: "ผู้ช่วย",
    panelFormat: "รูปแบบ",
    foldTools: "พับเครื่องมือ",
    openTools: "เปิดเครื่องมือ",
    promptTokenCount: "จำนวนแท็กพรอมป์",
    languageAndScope: "ภาษาและขอบเขตของเวิร์กเบนช์พรอมป์",
    languageSelector: "เมนูภาษาเวิร์กเบนช์พรอมป์",
    promptScope: "พรอมป์",
    negativeScope: "เนกาทีฟ",
    tagSingular: "แท็ก",
    tagPlural: "แท็ก",
    enterNewKeyword: "ป้อนคีย์เวิร์ดใหม่",
    keywordInput: "ช่องคีย์เวิร์ดของเวิร์กเบนช์พรอมป์",
    enterToAddKeyword: "กด Enter เพื่อเพิ่มคีย์เวิร์ด",
    preferencesShort: "ตั้งค่า",
    preferences: "การตั้งค่า",
    append: "เพิ่ม",
    noInlineSuggestions: "ยังไม่ได้โหลดคำแนะนำแบบอินไลน์.",
    groupTags: "แท็กกลุ่ม",
    showGroupTags: "แสดงแท็กกลุ่ม",
    hideGroupTags: "ซ่อนแท็กกลุ่ม",
    groupTagsHidden: "แท็กกลุ่มถูกซ่อนอยู่.",
    noGroupTags: "ยังไม่ได้โหลดแท็กกลุ่ม.",
  },
  id: {
    title: "Meja kerja prompt",
    subtitle: "Editor prompt terstruktur dengan riwayat, favorit, aturan format, dan pembersihan daftar hitam.",
    openWorkbench: "Buka meja kerja",
    hideWorkbench: "Sembunyikan meja kerja",
    promptTab: "Prompt",
    negativeTab: "Negatif",
    panelEditor: "Editor",
    panelHistory: "Riwayat",
    panelFavorites: "Favorit",
    panelCatalog: "Katalog",
    panelAssist: "Bantuan",
    panelFormat: "Format",
    foldTools: "Lipat alat",
    openTools: "Buka alat",
    promptTokenCount: "Jumlah tag prompt",
    languageAndScope: "Bahasa dan cakupan meja kerja prompt",
    languageSelector: "Menu bahasa meja kerja prompt",
    promptScope: "prompt",
    negativeScope: "negatif",
    tagSingular: "tag",
    tagPlural: "tag",
    enterNewKeyword: "Masukkan kata kunci baru",
    keywordInput: "Input kata kunci meja kerja prompt",
    enterToAddKeyword: "Tekan Enter untuk menambah kata kunci",
    preferencesShort: "Pref",
    preferences: "Preferensi",
    append: "Tambah",
    noInlineSuggestions: "Saran inline belum dimuat.",
    groupTags: "Tag grup",
    showGroupTags: "Tampilkan tag grup",
    hideGroupTags: "Sembunyikan tag grup",
    groupTagsHidden: "Tag grup disembunyikan.",
    noGroupTags: "Tag grup belum dimuat.",
  },
});

const INLINE_TOOLBAR_ICONS = Object.freeze({
  append: "➕",
  api: "API",
  autoInput: "⌨️",
  autoTranslate: "✅",
  blacklist: "▦",
  copy: "📋",
  delete: "🗑️",
  favorites: "🔖",
  fold: "🔼",
  format: "A↔B",
  history: "🕘",
  hotkey: "⌘",
  info: "ⓘ",
  open: "🧰",
  settings: "⚙️",
  theme: "🎨",
  tooltip: "Ⓣ",
  translate: "🌐",
});

const LANGUAGE_SELECTOR_VIEWPORT_MARGIN = 12;
const LANGUAGE_SELECTOR_MAX_WIDTH = 360;
const LANGUAGE_SELECTOR_MIN_WIDTH = 240;
const LANGUAGE_SELECTOR_MAX_HEIGHT = 320;

function normalizeDomIdPart(value) {
  return String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9_-]+/g, "-") || "option";
}

function normalizeTokenText(text) {
  return String(text ?? "").trim();
}

function classifyPromptToken(text) {
  const normalized = normalizeTokenText(text);
  const lower = normalized.toLowerCase();
  if (lower === "break") {
    return "break";
  }
  if (lower === "and" || lower.startsWith("and ")) {
    return "and";
  }
  if (lower.startsWith("<lora:")) {
    return "lora";
  }
  if (lower.startsWith("<lyco:") || lower.startsWith("<lycoris:")) {
    return "lycoris";
  }
  if (lower.startsWith("embedding:")) {
    return "embedding";
  }
  if (lower.startsWith("[") && lower.endsWith("]") && lower.includes(":")) {
    return "schedule";
  }
  if (extractTokenWeight(normalized) !== null || (normalized.startsWith("(") && normalized.endsWith(")"))) {
    return "weighted";
  }
  return "plain";
}

function extractTokenWeight(text) {
  const match = normalizeTokenText(text).match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (!match) {
    return null;
  }
  const value = Number.parseFloat(match[2]);
  return Number.isFinite(value) ? value : null;
}

function createToken(
  text,
  {
    disabled = false,
    selected = false,
    translatedText = "",
    scope = "prompt",
    orderIndex = 0,
  } = {},
) {
  tokenSequence += 1;
  const rawText = normalizeTokenText(text);
  return {
    id: `pw-token-${tokenSequence}`,
    text: rawText,
    raw_text: rawText,
    normalized_text: rawText.toLowerCase(),
    scope: String(scope ?? "prompt").trim() || "prompt",
    order_index: Number.isInteger(orderIndex) ? orderIndex : 0,
    disabled: Boolean(disabled),
    selected: Boolean(selected),
    translated_text: String(translatedText ?? ""),
    keyword_family: classifyPromptToken(rawText),
    weight: extractTokenWeight(rawText),
  };
}

function normalizeStatePayload(namespace, payload) {
  return {
    namespace,
    workbench_open: Boolean(payload?.workbench_open),
    active_panel: String(payload?.active_panel ?? "editor").trim() || "editor",
    draft_prompt: String(payload?.draft_prompt ?? ""),
    selected_entry_id: String(payload?.selected_entry_id ?? ""),
  };
}

function normalizePromptEntry(entry) {
  return {
    id: String(entry?.id ?? "").trim() || `pw-entry-${Date.now()}`,
    label: String(entry?.label ?? "").trim(),
    prompt_text: String(entry?.prompt_text ?? "").trim(),
    tag_tokens: Array.isArray(entry?.tag_tokens) ? entry.tag_tokens.map((token) => normalizeTokenText(token)).filter(Boolean) : [],
    token_payloads: Array.isArray(entry?.token_payloads) ? entry.token_payloads.map(normalizePersistedTokenPayload).filter(Boolean) : [],
    created_at: Number(entry?.created_at ?? 0) || 0,
  };
}

function normalizePersistedTokenPayload(token) {
  if (!token || typeof token !== "object") {
    return null;
  }
  const rawText = normalizeTokenText(token.raw_text ?? token.text);
  if (!rawText) {
    return null;
  }
  return {
    raw_text: rawText,
    normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
    scope: normalizeTokenText(token.scope),
    order_index: Number.isInteger(token.order_index) ? token.order_index : 0,
    disabled: Boolean(token.disabled),
    selected: Boolean(token.selected),
    translated_text: String(token.translated_text ?? ""),
    keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
    weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
  };
}

function setText(node, value) {
  if (node) {
    node.textContent = String(value ?? "");
  }
}

function countPromptUnits(value) {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return 0;
  }
  return trimmed.split(/[\s,]+/).filter(Boolean).length;
}

function splitPromptTokenText(text) {
  const source = String(text ?? "");
  const tokens = [];
  let current = "";
  let escaped = false;
  let parenDepth = 0;
  let bracketDepth = 0;
  let angleDepth = 0;

  for (const char of source) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      current += char;
      escaped = true;
      continue;
    }
    if (char === "<") {
      angleDepth += 1;
      current += char;
      continue;
    }
    if (char === ">" && angleDepth > 0) {
      angleDepth -= 1;
      current += char;
      continue;
    }
    if (char === "(" && angleDepth === 0) {
      parenDepth += 1;
      current += char;
      continue;
    }
    if (char === ")" && parenDepth > 0 && angleDepth === 0) {
      parenDepth -= 1;
      current += char;
      continue;
    }
    if (char === "[" && angleDepth === 0) {
      bracketDepth += 1;
      current += char;
      continue;
    }
    if (char === "]" && bracketDepth > 0 && angleDepth === 0) {
      bracketDepth -= 1;
      current += char;
      continue;
    }
    if ((char === "," || char === "\n") && parenDepth === 0 && bracketDepth === 0 && angleDepth === 0) {
      const normalized = normalizeTokenText(current);
      if (normalized) {
        tokens.push(normalized);
      }
      current = "";
      continue;
    }
    current += char;
  }

  const normalized = normalizeTokenText(current);
  if (normalized) {
    tokens.push(normalized);
  }
  return tokens;
}

function parsePromptTokens(text, { scope = "prompt" } = {}) {
  return splitPromptTokenText(text).map((entry, index) => createToken(entry, { scope, orderIndex: index }));
}

function buildPromptTextFromTokens(tokens) {
  return (Array.isArray(tokens) ? tokens : [])
    .filter((token) => token && !token.disabled && normalizeTokenText(token.raw_text ?? token.text))
    .map((token) => normalizeTokenText(token.raw_text ?? token.text))
    .join(", ");
}

function formatTokenWeight(value) {
  const rounded = Math.max(0, Math.round(Number(value) * 100) / 100);
  return String(rounded).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
}

function adjustPromptTokenWeight(text, delta) {
  const normalized = normalizeTokenText(text);
  if (!normalized) {
    return "";
  }
  const match = normalized.match(/^\((.+):([+-]?(?:\d+(?:\.\d+)?|\.\d+))\)$/);
  if (match) {
    return `(${match[1]}:${formatTokenWeight(Number.parseFloat(match[2]) + delta)})`;
  }
  return `(${normalized}:${delta >= 0 ? "1.1" : "0.9"})`;
}

function updateTokenText(token, nextText) {
  const rawText = normalizeTokenText(nextText);
  token.text = rawText;
  token.raw_text = rawText;
  token.normalized_text = rawText.toLowerCase();
  token.keyword_family = classifyPromptToken(rawText);
  token.weight = extractTokenWeight(rawText);
}

function formatPromptText(text, formattingRules) {
  let nextText = String(text ?? "");
  if (formattingRules?.normalize_spacing) {
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .join(", ");
  }
  if (formattingRules?.dedupe_commas) {
    const seen = new Set();
    nextText = nextText
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .filter((entry) => {
        const key = entry.toLowerCase();
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .join(", ");
  }
  if (formattingRules?.trim_outer_whitespace) {
    nextText = nextText.trim();
  }
  return nextText;
}

function buildEntryLabel(scope, promptText) {
  const preview = String(promptText ?? "").trim();
  if (!preview) {
    return scope === "negative" ? "Negative Prompt" : "Prompt";
  }
  const prefix = scope === "negative" ? "Negative" : "Prompt";
  return `${prefix}: ${preview.slice(0, 48)}`;
}

function clearChildren(node) {
  if (node) {
    node.replaceChildren();
  }
}

export function createPromptWorkbenchShell({
  idPrefix,
  parent,
  bootstrapState,
  promptInput,
  negativePromptInput,
  namespaces,
  appendTextElement,
  createActionButton,
  onStatusMessage,
  fixedScope = "",
} = {}) {
  const normalizedFixedScope = fixedScope === "prompt" || fixedScope === "negative" ? fixedScope : "";
  const shell = document.createElement("section");
  shell.id = `${idPrefix}-section`;
  shell.className = "rookieui-shell__prompt-workbench rookieui-shell__prompt-workbench-card-root";
  if (normalizedFixedScope) {
    shell.classList.add("rookieui-shell__prompt-workbench--inline");
  }
  shell.dataset.layout = normalizedFixedScope ? "prompt_all_in_one_inline" : "prompt_all_in_one";
  shell.dataset.scopeMode = normalizedFixedScope ? "fixed" : "paired";
  if (normalizedFixedScope) {
    shell.dataset.fixedScope = normalizedFixedScope;
  }
  shell.tabIndex = -1;
  parent.appendChild(shell);

  const configState = structuredClone(bootstrapState?.promptWorkbench?.config ?? {});
  configState.ui_preferences = configState.ui_preferences ?? {};
  configState.translation = configState.translation ?? { default_provider: "", providers: {} };
  configState.ai_assist = configState.ai_assist ?? {
    default_provider: "",
    providers: {},
    instruction_preset: "",
  };
  const blacklistState = structuredClone(bootstrapState?.promptWorkbench?.blacklist ?? { enabled: false, entries: [], translation_entries: [] });
  blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
  const hostActions = structuredClone(bootstrapState?.promptWorkbench?.host_actions ?? {});
  const languageOptions = Array.isArray(bootstrapState?.promptWorkbench?.language_options)
    ? bootstrapState.promptWorkbench.language_options
    : [];
  const themeStyleOptions = Array.isArray(bootstrapState?.promptWorkbench?.theme_style_options)
    ? bootstrapState.promptWorkbench.theme_style_options
    : [];
  const namespaceMap = {
    prompt: String(namespaces?.prompt ?? "").trim(),
    negative: String(namespaces?.negative ?? "").trim(),
  };
  const inputMap = {
    prompt: promptInput,
    negative: negativePromptInput,
  };
  const languageSyncSourceId = `${idPrefix}-${++promptWorkbenchInstanceSequence}`;
  const stateCache = new Map();
  const editorCache = new Map();
  const historyCache = new Map();
  const favoritesCache = new Map();
  const dirtyTimers = new Map();
  const autoHistoryTimers = new Map();
  const lastAutoHistoryText = new Map();
  const catalogSearchState = { query: "" };
  let providersPayload = null;
  let catalogPayload = null;
  let stateReadyPromise = null;
  let resourcesReadyPromise = null;
  let activeScope = normalizedFixedScope || "prompt";
  let activeSecondaryPopover = "";
  let languageSelectorOpen = false;
  let resourcesLoaded = false;
  let dragTokenId = "";
  const assistState = {
    imageDescription: "",
    generatedPrompt: "",
    generating: false,
  };
  const upsampleState = {
    running: false,
  };
  const importExportState = {
    jsonText: "",
    busy: false,
  };
  const t = (key) => {
    // IMPORTANT: supported selector languages may rely on language_options.fallback_code; keep UI copy fallback chain-aware.
    for (const language of getWorkbenchI18nChain(configState?.language ?? "en")) {
      const value = WORKBENCH_I18N[language]?.[key];
      if (value !== undefined) {
        return value;
      }
    }
    return WORKBENCH_I18N.en[key] ?? key;
  };
  const text = (key, replacements = {}) =>
    Object.entries(replacements).reduce(
      (value, [name, replacement]) => value.replaceAll(`{${name}}`, String(replacement ?? "")),
      t(key),
    );

  const header = document.createElement("div");
  header.className = "rookieui-shell__prompt-workbench-header";
  header.dataset.pwUi = "prompt-card-header";
  shell.appendChild(header);

  const headerCopy = document.createElement("div");
  headerCopy.className = "rookieui-shell__prompt-workbench-copy";
  header.appendChild(headerCopy);
  const titleNode = appendTextElement(headerCopy, "h5", "rookieui-shell__prompt-workbench-title", t("title"));
  const subtitleNode = appendTextElement(
    headerCopy,
    "p",
    "rookieui-shell__prompt-workbench-subtitle",
    t("subtitle"),
  );

  const headerActions = document.createElement("div");
  headerActions.className = "rookieui-shell__prompt-workbench-header-actions rookieui-shell__prompt-workbench-toolbar";
  headerActions.dataset.pwUi = "header-toolbar";
  header.appendChild(headerActions);

  const toggleButton = createActionButton(`${idPrefix}-toggle`, t("openWorkbench"));
  toggleButton.classList.add("rookieui-shell__prompt-workbench-toggle");
  toggleButton.dataset.pwUi = "fold-toggle";
  toggleButton.setAttribute("aria-controls", `${idPrefix}-body`);
  headerActions.appendChild(toggleButton);

  const inlineToolbarNodes = {
    counter: null,
    language: null,
    historyButton: null,
    favoritesButton: null,
    settingsButton: null,
    settingsHoverBox: null,
    appendButton: null,
    keywordInput: null,
    languageSelector: null,
  };

  const applyIconButtonLabel = (button, icon, label) => {
    button.textContent = icon;
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
  };

  const createInlineToolbarButton = (buttonId, icon, label, uiName, handler) => {
    const button = createActionButton(`${idPrefix}-${buttonId}`, icon);
    button.classList.add("rookieui-shell__prompt-workbench-inline-tool");
    button.dataset.pwUi = uiName;
    applyIconButtonLabel(button, icon, label);
    button.addEventListener("click", handler);
    headerActions.appendChild(button);
    return button;
  };

  const openInlinePanel = (panelId, surface = "") => {
    activeSecondaryPopover = surface;
    const state = getActiveState();
    state.workbench_open = true;
    state.active_panel = panelId;
    queueStatePersist();
    syncUi();
  };

  const createInlineSettingsHoverBox = () => {
    const box = document.createElement("div");
    box.id = `${idPrefix}-inline-settings-hoverbox`;
    box.className = "rookieui-shell__prompt-workbench-inline-settings-box";
    box.dataset.pwUi = "inline-settings-hoverbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", t("preferences"));

    const actionRow = document.createElement("div");
    actionRow.className = "rookieui-shell__prompt-workbench-inline-settings-row";
    box.appendChild(actionRow);

    const addDetailButton = (buttonId, icon, label, panelId, statusMessage = "") => {
      const button = createActionButton(`${idPrefix}-inline-settings-${buttonId}`, icon);
      button.classList.add("rookieui-shell__prompt-workbench-inline-setting-detail");
      button.dataset.pwUi = `inline-settings-${buttonId}`;
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
      button.addEventListener("click", () => {
        openInlinePanel(panelId, panelId === "format" ? "settings" : "");
        if (statusMessage) {
          updateStatus(statusMessage);
        }
      });
      actionRow.appendChild(button);
      return button;
    };

    addDetailButton("api", INLINE_TOOLBAR_ICONS.api, "Translation API settings", "assist");
    addDetailButton("format", INLINE_TOOLBAR_ICONS.format, "Prompt format settings", "format");
    addDetailButton("blacklist", INLINE_TOOLBAR_ICONS.blacklist, "Keywords blacklist", "format");
    addDetailButton("hotkey", INLINE_TOOLBAR_ICONS.hotkey, "Hotkey settings", "format", "Prompt Workbench hotkeys are scoped to the active editor");
    addDetailButton("theme", INLINE_TOOLBAR_ICONS.theme, "Theme settings", "assist");
    addDetailButton("about", INLINE_TOOLBAR_ICONS.info, "Prompt Workbench details", "assist", "Prompt Workbench inline prompt-all-in-one parity controls");

    const optionRow = document.createElement("div");
    optionRow.className = "rookieui-shell__prompt-workbench-inline-settings-row";
    box.appendChild(optionRow);

    const addOptionToggle = (key, icon, label, defaultChecked = false) => {
      const labelNode = document.createElement("label");
      labelNode.className = "rookieui-shell__prompt-workbench-inline-setting-toggle";
      labelNode.setAttribute("title", label);
      labelNode.setAttribute("aria-label", label);
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `${idPrefix}-inline-settings-${key.replace(/_/g, "-")}`;
      input.checked = Boolean(configState?.ui_preferences?.[key] ?? defaultChecked);
      input.addEventListener("change", () => {
        configState.ui_preferences = {
          ...(configState.ui_preferences ?? {}),
          [key]: input.checked,
        };
        queueConfigPersist();
      });
      labelNode.appendChild(input);
      appendTextElement(labelNode, "span", "rookieui-shell__prompt-workbench-inline-setting-icon", icon);
      optionRow.appendChild(labelNode);
      return input;
    };

    addOptionToggle("auto_translate", INLINE_TOOLBAR_ICONS.autoTranslate, "Auto translate new keywords");
    addOptionToggle("enable_tooltip", INLINE_TOOLBAR_ICONS.tooltip, "Enable keyword tooltips", true);

    const autoInputLabel = document.createElement("label");
    autoInputLabel.className = "rookieui-shell__prompt-workbench-inline-setting-select";
    autoInputLabel.setAttribute("title", "Auto input prompt after page load");
    appendTextElement(autoInputLabel, "span", "rookieui-shell__prompt-workbench-inline-setting-icon", INLINE_TOOLBAR_ICONS.autoInput);
    const autoInputSelect = document.createElement("select");
    autoInputSelect.id = `${idPrefix}-inline-settings-auto-input`;
    autoInputSelect.setAttribute("aria-label", "Auto input prompt after page load");
    [
      ["disabled", "Auto input: disabled"],
      ["last", "Last input prompt"],
    ].forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      autoInputSelect.appendChild(option);
    });
    autoInputSelect.value = String(configState?.ui_preferences?.auto_input_prompt ?? "disabled");
    autoInputSelect.addEventListener("change", () => {
      configState.ui_preferences = {
        ...(configState.ui_preferences ?? {}),
        auto_input_prompt: autoInputSelect.value,
      };
      queueConfigPersist();
    });
    autoInputLabel.appendChild(autoInputSelect);
    box.appendChild(autoInputLabel);

    return box;
  };

  const createInlineKeywordInput = () => {
    const input = document.createElement("textarea");
    input.id = `${idPrefix}-inline-keyword-input`;
    input.className = "rookieui-shell__prompt-workbench-inline-keyword-input";
    input.dataset.pwUi = "inline-keyword-input";
    input.rows = 1;
    input.placeholder = t("enterNewKeyword");
    input.setAttribute("aria-label", t("keywordInput"));
    input.setAttribute("title", t("enterToAddKeyword"));
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const value = normalizeTokenText(input.value);
      if (!value) {
        return;
      }
      appendPromptFragment(value, {
        statusMessage: text("groupTagInserted", { label: value }),
      });
      input.value = "";
    });
    return input;
  };

  if (normalizedFixedScope) {
    const counterChip = document.createElement("span");
    counterChip.id = `${idPrefix}-inline-counter`;
    counterChip.className = "rookieui-shell__prompt-workbench-inline-chip";
    counterChip.dataset.pwUi = "inline-counter";
    counterChip.setAttribute("role", "status");
    counterChip.setAttribute("aria-live", "polite");
    counterChip.setAttribute("aria-label", t("promptTokenCount"));
    counterChip.textContent = `0 ${t("tagPlural")}`;
    headerActions.appendChild(counterChip);
    inlineToolbarNodes.counter = counterChip;

    const languageButton = createActionButton(`${idPrefix}-inline-language`, "en");
    languageButton.classList.add("rookieui-shell__prompt-workbench-inline-chip", "rookieui-shell__prompt-workbench-language-button");
    languageButton.dataset.pwUi = "inline-language";
    languageButton.setAttribute("aria-label", t("languageAndScope"));
    languageButton.setAttribute("aria-haspopup", "listbox");
    languageButton.setAttribute("aria-controls", `${idPrefix}-language-selector`);
    languageButton.setAttribute("aria-expanded", "false");
    languageButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      languageSelectorOpen = !languageSelectorOpen;
      activeSecondaryPopover = "";
      syncUi();
      if (languageSelectorOpen) {
        focusSelectedLanguageOption();
      }
    });
    headerActions.appendChild(languageButton);
    inlineToolbarNodes.language = languageButton;

    const languageSelector = document.createElement("div");
    languageSelector.id = `${idPrefix}-language-selector`;
    languageSelector.className = "rookieui-shell__prompt-workbench-language-selector";
    languageSelector.dataset.pwUi = "language-selector-popover";
    languageSelector.setAttribute("role", "listbox");
    languageSelector.setAttribute("aria-label", t("languageSelector"));
    languageSelector.hidden = true;
    languageSelector.addEventListener("keydown", handleLanguageSelectorKeydown);
    headerActions.appendChild(languageSelector);
    inlineToolbarNodes.languageSelector = languageSelector;

    inlineToolbarNodes.historyButton = createInlineToolbarButton("inline-history", INLINE_TOOLBAR_ICONS.history, t("panelHistory"), "inline-history-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "history" ? "" : "history";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "history";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("historyLoaded") });
      syncUi();
    });
    inlineToolbarNodes.favoritesButton = createInlineToolbarButton("inline-favorites", INLINE_TOOLBAR_ICONS.favorites, t("panelFavorites"), "inline-favorites-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "favorites" ? "" : "favorites";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "favorites";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("favoritesLoaded") });
      syncUi();
    });
    const settingsCluster = document.createElement("span");
    settingsCluster.className = "rookieui-shell__prompt-workbench-inline-settings-cluster";
    settingsCluster.dataset.pwUi = "inline-settings-cluster";
    headerActions.appendChild(settingsCluster);
    inlineToolbarNodes.settingsButton = createActionButton(`${idPrefix}-inline-settings`, INLINE_TOOLBAR_ICONS.settings);
    inlineToolbarNodes.settingsButton.classList.add("rookieui-shell__prompt-workbench-inline-tool");
    inlineToolbarNodes.settingsButton.dataset.pwUi = "inline-settings-anchor";
    applyIconButtonLabel(inlineToolbarNodes.settingsButton, INLINE_TOOLBAR_ICONS.settings, t("preferencesShort"));
    inlineToolbarNodes.settingsButton.removeAttribute("title");
    inlineToolbarNodes.settingsButton.addEventListener("click", () => {
      activeSecondaryPopover = activeSecondaryPopover === "settings" ? "" : "settings";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "format";
      queueStatePersist();
      syncUi();
    });
    settingsCluster.appendChild(inlineToolbarNodes.settingsButton);
    inlineToolbarNodes.settingsHoverBox = createInlineSettingsHoverBox();
    settingsCluster.appendChild(inlineToolbarNodes.settingsHoverBox);
    [inlineToolbarNodes.historyButton, inlineToolbarNodes.favoritesButton, inlineToolbarNodes.settingsButton].forEach((button) => {
      button?.setAttribute("aria-haspopup", "dialog");
      button?.setAttribute("aria-controls", `${idPrefix}-secondary-popover`);
    });
    createInlineToolbarButton("inline-translate", INLINE_TOOLBAR_ICONS.translate, "Translate", "inline-translate-action", () => {
      translateActivePrompt(String(configState.language ?? "en").trim() || "en");
    });
    createInlineToolbarButton("inline-copy", INLINE_TOOLBAR_ICONS.copy, "Copy", "inline-copy-action", () => {
      const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "");
      if (navigator?.clipboard?.writeText) {
        void navigator.clipboard.writeText(promptText);
      }
      updateStatus(t("copiedActivePrompt"));
    });
    createInlineToolbarButton("inline-delete", INLINE_TOOLBAR_ICONS.delete, "Delete", "inline-delete-action", () => {
      applyPromptTextToInput("", {
        updateEditor: true,
        statusMessage: t("clearedActivePrompt"),
      });
    });
    inlineToolbarNodes.appendButton = createInlineToolbarButton("inline-append", INLINE_TOOLBAR_ICONS.append, t("append"), "inline-append-anchor", () => {
      activeSecondaryPopover = activeSecondaryPopover === "append" ? "" : "append";
      const state = getActiveState();
      state.workbench_open = true;
      state.active_panel = "editor";
      queueStatePersist();
      void ensureResourcesLoaded({ statusMessage: t("appendLoaded") });
      syncUi();
    });
    inlineToolbarNodes.appendButton.setAttribute("aria-haspopup", "dialog");
    inlineToolbarNodes.appendButton.setAttribute("aria-controls", `${idPrefix}-secondary-popover`);
    inlineToolbarNodes.keywordInput = createInlineKeywordInput();
    headerActions.appendChild(inlineToolbarNodes.keywordInput);
  }

  const body = document.createElement("div");
  body.id = `${idPrefix}-body`;
  body.className = "rookieui-shell__prompt-workbench-body rookieui-shell__prompt-workbench-card-body";
  body.dataset.pwUi = "prompt-card-body";
  shell.appendChild(body);

  const namespaceTabs = document.createElement("div");
  namespaceTabs.className = "rookieui-shell__prompt-workbench-tabs";
  namespaceTabs.dataset.pwUi = "scope-tabs";
  namespaceTabs.hidden = Boolean(normalizedFixedScope);
  body.appendChild(namespaceTabs);

  const tabButtons = new Map();
  const createScopeButton = (scope, label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-tab-${scope}`;
    button.className = "rookieui-shell__prompt-workbench-tab";
    button.textContent = label;
    button.addEventListener("click", () => {
      activeScope = scope;
      syncUi();
    });
    namespaceTabs.appendChild(button);
    tabButtons.set(scope, button);
  };
  createScopeButton("prompt", t("promptTab"));
  createScopeButton("negative", t("negativeTab"));

  const summaryGrid = document.createElement("div");
  summaryGrid.className = "rookieui-shell__prompt-workbench-summary-grid rookieui-shell__prompt-workbench-status-strip";
  summaryGrid.dataset.pwUi = "status-strip";
  body.appendChild(summaryGrid);

  const summaryLabels = new Map();
  const createSummaryCard = (key, label) => {
    const card = document.createElement("article");
    card.className = "rookieui-shell__prompt-workbench-card";
    const labelNode = appendTextElement(card, "span", "rookieui-shell__prompt-workbench-card-label", label);
    summaryLabels.set(key, labelNode);
    const value = document.createElement("strong");
    value.id = `${idPrefix}-${key}`;
    value.className = "rookieui-shell__prompt-workbench-card-value";
    card.appendChild(value);
    summaryGrid.appendChild(card);
    return value;
  };

  const summaryNodes = {
    state: createSummaryCard("state", t("summaryState")),
    providers: createSummaryCard("providers", t("summaryProviders")),
    catalogs: createSummaryCard("catalogs", t("summaryCatalogs")),
    history: createSummaryCard("history", t("summaryHistory")),
    favorites: createSummaryCard("favorites", t("summaryFavorites")),
    blacklist: createSummaryCard("blacklist", t("summaryBlacklist")),
  };

  const panelRail = document.createElement("div");
  panelRail.className = "rookieui-shell__prompt-workbench-panel-rail";
  body.appendChild(panelRail);

  const panelButtons = new Map();
  ["editor", "history", "favorites", "catalog", "assist", "format"].forEach((panelId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${idPrefix}-panel-${panelId}`;
    button.className = "rookieui-shell__prompt-workbench-panel-button";
    button.textContent = t(`panel${panelId.charAt(0).toUpperCase()}${panelId.slice(1)}`);
    button.addEventListener("click", () => {
      const currentState = getActiveState();
      currentState.active_panel = panelId;
      queueStatePersist();
      syncUi();
    });
    panelRail.appendChild(button);
    panelButtons.set(panelId, button);
  });

  const secondaryRow = document.createElement("div");
  secondaryRow.className = "rookieui-shell__prompt-workbench-secondary-entrypoints";
  secondaryRow.dataset.pwUi = "secondary-entrypoints";
  body.appendChild(secondaryRow);

  const secondaryButtons = new Map();
  const createSecondaryButton = (surface, label, panelId = surface) => {
    const button = createActionButton(`${idPrefix}-quick-${surface}`, label);
    button.classList.add("rookieui-shell__prompt-workbench-secondary-button");
    button.dataset.pwUi = surface === "settings" ? "settings-menu-entrypoint" : `${surface}-popover-entrypoint`;
    button.addEventListener("click", () => {
      activeSecondaryPopover = activeSecondaryPopover === surface ? "" : surface;
      const currentState = getActiveState();
      currentState.active_panel = panelId;
      queueStatePersist();
      syncUi();
    });
    secondaryRow.appendChild(button);
    secondaryButtons.set(surface, button);
    return button;
  };

  createSecondaryButton("history", t("panelHistory"));
  createSecondaryButton("favorites", t("panelFavorites"));
  createSecondaryButton("settings", t("preferencesShort"), "format");

  const secondaryPopover = document.createElement("div");
  secondaryPopover.id = `${idPrefix}-secondary-popover`;
  secondaryPopover.className = "rookieui-shell__prompt-workbench-secondary-popover";
  secondaryPopover.dataset.pwUi = "history-favorites-popovers";
  secondaryPopover.hidden = true;
  body.appendChild(secondaryPopover);

  const actionsRow = document.createElement("div");
  actionsRow.className = "rookieui-shell__prompt-workbench-actions";
  body.appendChild(actionsRow);

  const captureButton = createActionButton(`${idPrefix}-capture`, t("captureCurrentText"));
  captureButton.addEventListener("click", () => {
    const input = getActiveInput();
    const nextText = String(input?.value ?? "");
    const state = getActiveState();
    state.draft_prompt = nextText;
    editorCache.set(getActiveNamespace(), parsePromptTokens(nextText, { scope: activeScope }));
    queueStatePersist();
    syncUi();
    onStatusMessage?.("Captured current prompt text into Prompt Workbench state");
  });
  actionsRow.appendChild(captureButton);

  const restoreButton = createActionButton(`${idPrefix}-restore`, t("restoreDraft"));
  restoreButton.addEventListener("click", () => {
    applyPromptTextToInput(getActiveState().draft_prompt, {
      updateEditor: true,
      statusMessage: "Restored saved Prompt Workbench draft into the active prompt field",
    });
  });
  actionsRow.appendChild(restoreButton);

  const panelContent = document.createElement("div");
  panelContent.className = "rookieui-shell__prompt-workbench-panel-content";
  body.appendChild(panelContent);

  const editorPane = document.createElement("section");
  editorPane.id = `${idPrefix}-editor-pane`;
  editorPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(editorPane);

  const historyPane = document.createElement("section");
  historyPane.id = `${idPrefix}-history-pane`;
  historyPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(historyPane);

  const favoritesPane = document.createElement("section");
  favoritesPane.id = `${idPrefix}-favorites-pane`;
  favoritesPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(favoritesPane);

  const catalogPane = document.createElement("section");
  catalogPane.id = `${idPrefix}-catalog-pane`;
  catalogPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(catalogPane);

  const formatPane = document.createElement("section");
  formatPane.id = `${idPrefix}-format-pane`;
  formatPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(formatPane);

  const assistPane = document.createElement("section");
  assistPane.id = `${idPrefix}-assist-pane`;
  assistPane.className = "rookieui-shell__prompt-workbench-pane";
  panelContent.appendChild(assistPane);

  const details = document.createElement("div");
  details.className = "rookieui-shell__prompt-workbench-details";
  body.appendChild(details);

  const detailNodes = {
    scope: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    draft: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    panel: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-detail", ""),
    status: appendTextElement(details, "p", "rookieui-shell__prompt-workbench-status", t("ready")),
  };

  function getLanguageOptions() {
    const options = (languageOptions.length ? languageOptions : [{ code: "en", title: "English" }])
      .map((entry) => ({
        code: String(entry?.code ?? "en").trim() || "en",
        title: String(entry?.title ?? entry?.code ?? "English").trim() || "English",
        nativeTitle: String(entry?.native_title ?? entry?.title ?? entry?.code ?? "English").trim() || "English",
        aliases: Array.isArray(entry?.aliases)
          ? entry.aliases.map((alias) => String(alias ?? "").trim()).filter(Boolean)
          : [],
        fallbackCode: String(entry?.fallback_code ?? "en").trim() || "en",
      }))
      .filter((entry) => entry.code);
    return options.length ? options : [{ code: "en", title: "English", nativeTitle: "English", aliases: [], fallbackCode: "en" }];
  }

  function getLanguageAliasKey(value) {
    return String(value ?? "").trim().replace(/_/g, "-").toLowerCase();
  }

  function normalizeLanguageCode(value) {
    const aliases = new Map();
    getLanguageOptions().forEach((entry) => {
      aliases.set(getLanguageAliasKey(entry.code), entry.code);
      entry.aliases.forEach((alias) => {
        aliases.set(getLanguageAliasKey(alias), entry.code);
      });
    });
    return aliases.get(getLanguageAliasKey(value)) ?? aliases.get("en") ?? "en";
  }

  function getLanguageOption(code) {
    const normalizedCode = getLanguageAliasKey(code);
    return getLanguageOptions().find((entry) => getLanguageAliasKey(entry.code) === normalizedCode) ?? null;
  }

  function getWorkbenchI18nChain(value) {
    const chain = [];
    const seen = new Set();
    const append = (code) => {
      const normalizedCode = String(code ?? "").trim();
      if (!normalizedCode || seen.has(normalizedCode)) {
        return;
      }
      seen.add(normalizedCode);
      if (WORKBENCH_I18N[normalizedCode]) {
        chain.push(normalizedCode);
      }
    };

    let cursor = normalizeLanguageCode(value);
    for (let index = 0; index < 8 && cursor && !seen.has(`fallback:${cursor}`); index += 1) {
      seen.add(`fallback:${cursor}`);
      append(cursor);
      const option = getLanguageOption(cursor);
      const fallbackCode = normalizeLanguageCode(option?.fallbackCode ?? "");
      if (!fallbackCode || fallbackCode === cursor) {
        break;
      }
      cursor = fallbackCode;
    }

    const selectedLanguage = normalizeLanguageCode(value);
    const baseLanguage = selectedLanguage.includes("-") ? selectedLanguage.split("-")[0] : "";
    append(baseLanguage);
    append("en");
    return chain.length ? chain : ["en"];
  }

  function closeLanguageSelector({ focusTrigger = false } = {}) {
    if (!languageSelectorOpen) {
      return;
    }
    languageSelectorOpen = false;
    syncUi();
    if (focusTrigger) {
      inlineToolbarNodes.language?.focus();
    }
  }

  function getViewportSize() {
    const viewport = globalThis?.visualViewport;
    const width = Number(viewport?.width ?? globalThis?.innerWidth ?? document?.documentElement?.clientWidth ?? 1024);
    const height = Number(viewport?.height ?? globalThis?.innerHeight ?? document?.documentElement?.clientHeight ?? 768);
    return {
      width: Number.isFinite(width) && width > 0 ? width : 1024,
      height: Number.isFinite(height) && height > 0 ? height : 768,
    };
  }

  function clampOverlayValue(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(Math.max(value, min), max);
  }

  function placeLanguageSelector() {
    const selector = inlineToolbarNodes.languageSelector;
    const trigger = inlineToolbarNodes.language;
    if (!selector || !trigger || selector.hidden) {
      return;
    }
    const viewport = getViewportSize();
    const rect = trigger.getBoundingClientRect?.() ?? { left: LANGUAGE_SELECTOR_VIEWPORT_MARGIN, bottom: LANGUAGE_SELECTOR_VIEWPORT_MARGIN };
    const availableWidth = Math.max(160, viewport.width - LANGUAGE_SELECTOR_VIEWPORT_MARGIN * 2);
    const width = Math.min(LANGUAGE_SELECTOR_MAX_WIDTH, Math.max(LANGUAGE_SELECTOR_MIN_WIDTH, Math.min(availableWidth, Math.round(availableWidth))));
    const left = clampOverlayValue(
      Math.round(Number(rect.left ?? LANGUAGE_SELECTOR_VIEWPORT_MARGIN)),
      LANGUAGE_SELECTOR_VIEWPORT_MARGIN,
      viewport.width - width - LANGUAGE_SELECTOR_VIEWPORT_MARGIN,
    );
    const topCandidate = Math.round(Number(rect.bottom ?? LANGUAGE_SELECTOR_VIEWPORT_MARGIN) + 6);
    const maxHeight = Math.min(
      LANGUAGE_SELECTOR_MAX_HEIGHT,
      Math.max(120, viewport.height - topCandidate - LANGUAGE_SELECTOR_VIEWPORT_MARGIN),
    );
    const top = clampOverlayValue(topCandidate, LANGUAGE_SELECTOR_VIEWPORT_MARGIN, viewport.height - maxHeight - LANGUAGE_SELECTOR_VIEWPORT_MARGIN);

    selector.dataset.placement = "fixed";
    selector.style.position = "fixed";
    selector.style.left = `${left}px`;
    selector.style.top = `${top}px`;
    selector.style.width = `${width}px`;
    selector.style.maxHeight = `${maxHeight}px`;
  }

  function getLanguageOptionButtons() {
    return Array.from(inlineToolbarNodes.languageSelector?.querySelectorAll("[data-pw-ui='language-option']") ?? []);
  }

  function focusLanguageOptionByIndex(index) {
    const options = getLanguageOptionButtons();
    if (!options.length) {
      return;
    }
    const nextIndex = clampOverlayValue(index, 0, options.length - 1);
    const nextOption = options[nextIndex];
    inlineToolbarNodes.languageSelector?.setAttribute("aria-activedescendant", nextOption.id);
    nextOption.focus();
  }

  function focusSelectedLanguageOption() {
    const options = getLanguageOptionButtons();
    const selectedIndex = options.findIndex((option) => option.dataset.selected === "true");
    focusLanguageOptionByIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }

  function focusRelativeLanguageOption(offset) {
    const options = getLanguageOptionButtons();
    if (!options.length) {
      return;
    }
    const activeIndex = options.findIndex((option) => option === document.activeElement);
    const selectedIndex = options.findIndex((option) => option.dataset.selected === "true");
    const currentIndex = activeIndex >= 0 ? activeIndex : selectedIndex >= 0 ? selectedIndex : 0;
    focusLanguageOptionByIndex(currentIndex + offset);
  }

  function handleLanguageSelectorKeydown(event) {
    if (!languageSelectorOpen) {
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeLanguageSelector({ focusTrigger: true });
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusRelativeLanguageOption(1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      focusRelativeLanguageOption(-1);
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      focusLanguageOptionByIndex(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      focusLanguageOptionByIndex(getLanguageOptionButtons().length - 1);
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      const eventOption = event.target?.dataset?.pwUi === "language-option" ? event.target : null;
      const activeOption = eventOption ?? (document.activeElement?.dataset?.pwUi === "language-option"
        ? document.activeElement
        : inlineToolbarNodes.languageSelector?.querySelector("[data-selected='true']"));
      const languageCode = activeOption?.dataset?.languageCode;
      if (languageCode) {
        event.preventDefault();
        setPromptWorkbenchLanguage(languageCode, { focusTrigger: true });
      }
    }
  }

  function setPromptWorkbenchLanguage(nextLanguage, { focusTrigger = false, broadcast = true } = {}) {
    const normalizedLanguage = normalizeLanguageCode(nextLanguage);
    const didChange = String(configState.language ?? "en").trim() !== normalizedLanguage;
    if (String(configState.language ?? "en").trim() !== normalizedLanguage) {
      configState.language = normalizedLanguage;
      queueConfigPersist();
    }
    languageSelectorOpen = false;
    syncUi();
    if (didChange && resourcesLoaded) {
      void refreshCatalogForLanguage(normalizedLanguage);
    }
    if (broadcast) {
      // IMPORTANT: prompt and negative inline shells own separate state; broadcast language changes so their chips cannot drift apart.
      document.dispatchEvent(
        new CustomEvent(PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT, {
          detail: {
            language: normalizedLanguage,
            sourceId: languageSyncSourceId,
          },
        }),
      );
    }
    if (focusTrigger) {
      inlineToolbarNodes.language?.focus();
    }
  }

  function handlePromptWorkbenchLanguageSync(event) {
    const detail = event?.detail ?? {};
    if (detail.sourceId === languageSyncSourceId) {
      return;
    }
    if (!shell.isConnected) {
      document.removeEventListener(PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT, handlePromptWorkbenchLanguageSync);
      return;
    }
    const normalizedLanguage = normalizeLanguageCode(detail.language);
    const didChange = String(configState.language ?? "en").trim() !== normalizedLanguage;
    configState.language = normalizedLanguage;
    languageSelectorOpen = false;
    syncUi();
    if (didChange && resourcesLoaded) {
      void refreshCatalogForLanguage(normalizedLanguage);
    }
  }

  document.addEventListener(PROMPT_WORKBENCH_LANGUAGE_SYNC_EVENT, handlePromptWorkbenchLanguageSync);

  async function refreshCatalogForLanguage(language) {
    const normalizedLanguage = normalizeLanguageCode(language);
    try {
      const result = await bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(normalizedLanguage);
      if (result?.data) {
        catalogPayload = result.data;
      }
      updateStatus(`Prompt Workbench catalog refreshed for ${normalizedLanguage}`);
    } catch {
      updateStatus(`Prompt Workbench catalog refresh failed for ${normalizedLanguage}`);
    } finally {
      syncUi();
    }
  }

  function renderLanguageSelector() {
    const selector = inlineToolbarNodes.languageSelector;
    if (!selector) {
      return;
    }
    clearChildren(selector);
    selector.hidden = !languageSelectorOpen;
    const currentLanguage = normalizeLanguageCode(configState?.language ?? "en");
    if (configState.language !== currentLanguage) {
      configState.language = currentLanguage;
    }
    selector.setAttribute("aria-activedescendant", `${idPrefix}-language-option-${normalizeDomIdPart(currentLanguage)}`);
    getLanguageOptions().forEach((entry) => {
      const displayTitle = entry.nativeTitle && entry.nativeTitle !== entry.title
        ? `${entry.code} - ${entry.title} (${entry.nativeTitle})`
        : `${entry.code} - ${entry.title}`;
      const optionButton = createActionButton(`${idPrefix}-language-option-${normalizeDomIdPart(entry.code)}`, displayTitle);
      optionButton.classList.add("rookieui-shell__prompt-workbench-language-option");
      optionButton.dataset.pwUi = "language-option";
      optionButton.dataset.languageCode = entry.code;
      optionButton.dataset.selected = String(entry.code === currentLanguage);
      optionButton.setAttribute("role", "option");
      optionButton.setAttribute("aria-selected", String(entry.code === currentLanguage));
      optionButton.addEventListener("focus", () => {
        selector.setAttribute("aria-activedescendant", optionButton.id);
      });
      optionButton.addEventListener("click", () => {
        setPromptWorkbenchLanguage(entry.code, { focusTrigger: true });
      });
      selector.appendChild(optionButton);
    });
    placeLanguageSelector();
  }

  function getActiveNamespace() {
    return namespaceMap[activeScope];
  }

  function getActiveInput() {
    return inputMap[activeScope] ?? null;
  }

  function getNamespaceInput(namespace) {
    if (namespace === namespaceMap.prompt) {
      return inputMap.prompt;
    }
    if (namespace === namespaceMap.negative) {
      return inputMap.negative;
    }
    return null;
  }

  function getActiveState() {
    const namespace = getActiveNamespace();
    if (!stateCache.has(namespace)) {
      stateCache.set(namespace, normalizeStatePayload(namespace, { draft_prompt: getActiveInput()?.value ?? "" }));
    }
    return stateCache.get(namespace);
  }

  function ensureEditorTokens(namespace) {
    if (!editorCache.has(namespace)) {
      const state = stateCache.get(namespace) ?? normalizeStatePayload(namespace, { draft_prompt: getNamespaceInput(namespace)?.value ?? "" });
      editorCache.set(namespace, parsePromptTokens(state.draft_prompt || getNamespaceInput(namespace)?.value, { scope: activeScope }));
    }
    return editorCache.get(namespace);
  }

  function setBodyOpen(isOpen) {
    shell.dataset.open = String(isOpen);
    shell.dataset.folded = String(!isOpen);
    body.hidden = !isOpen;
    if (normalizedFixedScope) {
      applyIconButtonLabel(toggleButton, isOpen ? INLINE_TOOLBAR_ICONS.fold : INLINE_TOOLBAR_ICONS.open, isOpen ? t("foldTools") : t("openTools"));
    } else {
      toggleButton.textContent = isOpen ? t("hideWorkbench") : t("openWorkbench");
    }
    toggleButton.setAttribute("aria-expanded", String(isOpen));
  }

  function readPreferredOpenState() {
    const state = getActiveState();
    if (state.workbench_open) {
      return true;
    }
    return Boolean(configState?.ui_preferences?.default_open);
  }

  function isPanelVisible(panelId) {
    if (panelId === "history") {
      return configState?.ui_preferences?.show_history !== false;
    }
    if (panelId === "favorites") {
      return configState?.ui_preferences?.show_favorites !== false;
    }
    return true;
  }

  function resolveVisiblePanel(panelId) {
    if (panelId && isPanelVisible(panelId)) {
      return panelId;
    }
    const preferredPanel = normalizeTokenText(configState?.ui_preferences?.preferred_panel) || "editor";
    if (isPanelVisible(preferredPanel)) {
      return preferredPanel;
    }
    return "editor";
  }

  function updateStatus(message) {
    setText(detailNodes.status, message);
  }

  function syncLocalizedUiLabels() {
    setText(titleNode, t("title"));
    setText(subtitleNode, t("subtitle"));
    tabButtons.get("prompt").textContent = t("promptTab");
    tabButtons.get("negative").textContent = t("negativeTab");
    summaryLabels.get("state").textContent = t("summaryState");
    summaryLabels.get("providers").textContent = t("summaryProviders");
    summaryLabels.get("catalogs").textContent = t("summaryCatalogs");
    summaryLabels.get("history").textContent = t("summaryHistory");
    summaryLabels.get("favorites").textContent = t("summaryFavorites");
    summaryLabels.get("blacklist").textContent = t("summaryBlacklist");
    panelButtons.forEach((button, panelId) => {
      button.textContent = t(`panel${panelId.charAt(0).toUpperCase()}${panelId.slice(1)}`);
    });
    secondaryButtons.get("history").textContent = t("panelHistory");
    secondaryButtons.get("favorites").textContent = t("panelFavorites");
    secondaryButtons.get("settings").textContent = t("preferencesShort");
    captureButton.textContent = t("captureCurrentText");
    restoreButton.textContent = t("restoreDraft");
    if (inlineToolbarNodes.counter) {
      inlineToolbarNodes.counter.setAttribute("aria-label", t("promptTokenCount"));
    }
    if (inlineToolbarNodes.language) {
      inlineToolbarNodes.language.setAttribute("aria-label", t("languageAndScope"));
    }
    if (inlineToolbarNodes.languageSelector) {
      inlineToolbarNodes.languageSelector.setAttribute("aria-label", t("languageSelector"));
    }
    if (inlineToolbarNodes.keywordInput) {
      inlineToolbarNodes.keywordInput.placeholder = t("enterNewKeyword");
      inlineToolbarNodes.keywordInput.setAttribute("aria-label", t("keywordInput"));
      inlineToolbarNodes.keywordInput.setAttribute("title", t("enterToAddKeyword"));
    }
    if (inlineToolbarNodes.historyButton) {
      applyIconButtonLabel(inlineToolbarNodes.historyButton, INLINE_TOOLBAR_ICONS.history, t("panelHistory"));
    }
    if (inlineToolbarNodes.favoritesButton) {
      applyIconButtonLabel(inlineToolbarNodes.favoritesButton, INLINE_TOOLBAR_ICONS.favorites, t("panelFavorites"));
    }
    if (inlineToolbarNodes.settingsButton) {
      applyIconButtonLabel(inlineToolbarNodes.settingsButton, INLINE_TOOLBAR_ICONS.settings, t("preferencesShort"));
      inlineToolbarNodes.settingsButton.removeAttribute("title");
    }
    if (inlineToolbarNodes.appendButton) {
      applyIconButtonLabel(inlineToolbarNodes.appendButton, INLINE_TOOLBAR_ICONS.append, t("append"));
    }
  }

  function queueStatePersist(namespaceOverride = "") {
    const namespace = normalizeTokenText(namespaceOverride) || getActiveNamespace();
    const state =
      stateCache.get(namespace) ??
      normalizeStatePayload(namespace, { draft_prompt: getNamespaceInput(namespace)?.value ?? "" });
    stateCache.set(namespace, state);
    const existingTimer = dirtyTimers.get(namespace);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    const nextTimer = setTimeout(async () => {
      dirtyTimers.delete(namespace);
      const result = await bootstrapState?.updatePromptWorkbenchStateRequest?.(namespace, {
        workbench_open: state.workbench_open,
        active_panel: state.active_panel,
        draft_prompt: state.draft_prompt,
        selected_entry_id: state.selected_entry_id,
      });
      updateStatus(result?.ok === false ? "Prompt Workbench state saved with fallback semantics" : "Prompt Workbench state synchronized");
      syncUi();
    }, 180);
    dirtyTimers.set(namespace, nextTimer);
  }

  function serializeTokenPayload(token, index) {
    const rawText = normalizeTokenText(token?.raw_text ?? token?.text);
    if (!rawText) {
      return null;
    }
    return {
      raw_text: rawText,
      normalized_text: normalizeTokenText(token.normalized_text) || rawText.toLowerCase(),
      scope: normalizeTokenText(token.scope) || activeScope,
      order_index: Number.isInteger(token.order_index) ? token.order_index : index,
      disabled: Boolean(token.disabled),
      selected: Boolean(token.selected),
      translated_text: String(token.translated_text ?? ""),
      keyword_family: normalizeTokenText(token.keyword_family) || classifyPromptToken(rawText),
      weight: Number.isFinite(Number(token.weight)) ? Number(token.weight) : null,
    };
  }

  function serializeTokenPayloads(tokens) {
    return (Array.isArray(tokens) ? tokens : []).map(serializeTokenPayload).filter(Boolean);
  }

  function buildCollectionItem(scope, promptText, tokens) {
    const tokenPayloads = serializeTokenPayloads(tokens);
    return {
      label: buildEntryLabel(scope, promptText),
      prompt_text: String(promptText ?? "").trim(),
      tag_tokens: tokenPayloads.filter((token) => !token.disabled).map((token) => token.raw_text),
      token_payloads: tokenPayloads,
    };
  }

  function queueAutoHistoryCapture(namespace, scope, promptText, tokens) {
    const normalizedText = String(promptText ?? "").trim();
    if (!namespace || !normalizedText || normalizedText === lastAutoHistoryText.get(namespace)) {
      return;
    }
    const existingTimer = autoHistoryTimers.get(namespace);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    const tokenSnapshot = serializeTokenPayloads(tokens);
    const nextTimer = setTimeout(() => {
      autoHistoryTimers.delete(namespace);
      if (normalizedText === lastAutoHistoryText.get(namespace)) {
        return;
      }
      lastAutoHistoryText.set(namespace, normalizedText);
      void bootstrapState?.updatePromptWorkbenchHistoryRequest?.(namespace, "auto_capture", {
        item: buildCollectionItem(scope, normalizedText, tokenSnapshot),
      }).then((result) => {
        const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
        historyCache.set(namespace, normalizedItems);
        updateStatus("Auto-saved prompt history");
        syncUi();
      });
    }, 600);
    autoHistoryTimers.set(namespace, nextTimer);
  }

  function queueConfigPersist() {
    void bootstrapState?.updatePromptWorkbenchConfigRequest?.(configState).then((result) => {
      if (result?.data?.config) {
        Object.assign(configState, result.data.config);
      }
      updateStatus(result?.ok === false ? "Formatting preferences saved with fallback semantics" : "Formatting preferences synchronized");
      syncUi();
    });
  }

  function getTranslationProviders() {
    return Array.isArray(providersPayload?.surfaces?.translation?.providers)
      ? providersPayload.surfaces.translation.providers.filter((entry) => entry?.execution_state === "shipped")
      : [];
  }

  function getAiAssistProviders() {
    return Array.isArray(providersPayload?.surfaces?.ai_assist?.providers)
      ? providersPayload.surfaces.ai_assist.providers.filter((entry) => entry?.execution_state === "shipped")
      : [];
  }

  function getDanbooruUpsampleAction() {
    const action = hostActions?.danbooru_upsample;
    if (action && typeof action === "object") {
      return action;
    }
    return {
      action_id: "danbooru_upsample",
      title: "Upsample Tags",
      route_path: "/rookieui/prompt-tools/upsample",
      available: false,
      resolved_node_alias: "",
      availability: {
        status: "host_missing",
        detail: "Host-installed Danbooru upsampler node is not available in the active ComfyUI registry.",
      },
    };
  }

  function getCatalogHighlight(entry, fallback = "plain") {
    return normalizeTokenText(entry?.highlight ?? entry?.category) || fallback;
  }

  function getTokenHighlight(token) {
    const tokenFamily = normalizeTokenText(token?.keyword_family) || "plain";
    const tokenFamilyHighlights = catalogPayload?.catalog_highlights?.token_families ?? {};
    return normalizeTokenText(tokenFamilyHighlights[tokenFamily]?.highlight) || tokenFamily;
  }

  function appendPromptFragment(fragment, { replace = false, statusMessage = "" } = {}) {
    const normalizedFragment = String(fragment ?? "").trim();
    if (!normalizedFragment) {
      return;
    }
    const currentText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    const nextText = replace || !currentText ? normalizedFragment : `${currentText}, ${normalizedFragment}`;
    applyPromptTextToInput(nextText, {
      updateEditor: true,
      statusMessage: statusMessage || "Updated prompt from Prompt Workbench catalog action",
    });
  }

  function persistTranslationProviderSelection(providerId) {
    configState.translation = {
      ...(configState.translation ?? {}),
      default_provider: String(providerId ?? "").trim(),
      providers: configState.translation?.providers ?? {},
    };
    queueConfigPersist();
  }

  function persistAiAssistProviderSelection(providerId) {
    configState.ai_assist = {
      ...(configState.ai_assist ?? {}),
      default_provider: String(providerId ?? "").trim(),
      providers: configState.ai_assist?.providers ?? {},
      instruction_preset: String(configState.ai_assist?.instruction_preset ?? ""),
    };
    queueConfigPersist();
  }

  function updateShellThemeStyle() {
    shell.dataset.themeStyle = String(configState?.theme_style ?? "rookieui_classic").trim() || "rookieui_classic";
  }

  function translateActivePrompt(targetLanguage) {
    const providerId = String(configState.translation?.default_provider ?? "").trim();
    const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    if (!providerId) {
      updateStatus("Select a shipped translation provider before translating");
      return;
    }
    if (!promptText) {
      updateStatus("No prompt text is available for translation");
      return;
    }
    updateStatus("Translating prompt text...");
    void bootstrapState
      ?.translatePromptWorkbenchRequest?.({
        provider: providerId,
        from_lang: "auto",
        to_lang: targetLanguage,
        text: promptText,
      })
      .then((result) => {
        const translatedText = String(result?.data?.translated_text ?? "").trim();
        if (!translatedText) {
          updateStatus("Translation response did not include translated text");
          return;
        }
        applyPromptTextToInput(translatedText, {
          updateEditor: true,
          statusMessage: `Translated prompt text to ${targetLanguage}`,
        });
      })
      .catch(() => {
        updateStatus("Prompt translation failed");
      });
  }

  function translateTokenBatch(tokens, targetLanguage) {
    const providerId = String(configState.translation?.default_provider ?? "").trim();
    const selectedTokens = (Array.isArray(tokens) ? tokens : []).filter(Boolean);
    if (!selectedTokens.length) {
      updateStatus("Select one or more prompt tokens before translating");
      return;
    }
    if (!providerId) {
      updateStatus("Select a shipped translation provider before translating");
      return;
    }
    const texts = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean);
    if (!texts.length) {
      updateStatus("No prompt tokens are available for translation");
      return;
    }
    updateStatus("Translating selected prompt tokens...");
    void bootstrapState
      ?.translatePromptWorkbenchRequest?.({
        provider: providerId,
        from_lang: "auto",
        to_lang: targetLanguage,
        texts,
        dictionary_first: true,
      })
      .then((result) => {
        const translatedTexts = Array.isArray(result?.data?.translated_texts) ? result.data.translated_texts : [];
        selectedTokens.forEach((token, index) => {
          const translatedText = String(translatedTexts[index] ?? "").trim();
          if (translatedText) {
            token.translated_text = translatedText;
          }
        });
        updateStatus("Translated selected prompt tokens");
        syncUi();
      })
      .catch(() => {
        updateStatus("Prompt token translation failed");
      });
  }

  function requestDanbooruUpsample() {
    const action = getDanbooruUpsampleAction();
    const availability = action?.availability ?? {};
    const availabilityStatus = String(availability?.status ?? "").trim() || "host_missing";
    const promptText = String(getActiveState().draft_prompt || getActiveInput()?.value || "").trim();
    const negativePromptText = String(inputMap.negative?.value ?? stateCache.get(namespaceMap.negative)?.draft_prompt ?? "").trim();
    if (activeScope !== "prompt") {
      updateStatus("Upsample Tags is only available for the primary prompt scope");
      return;
    }
    if (!promptText) {
      updateStatus("No prompt text is available for tag upsampling");
      return;
    }
    if (!Boolean(action?.available) || availabilityStatus !== "ready") {
      updateStatus(String(availability?.detail ?? "Danbooru upsampler host action is unavailable."));
      return;
    }
    upsampleState.running = true;
    updateStatus("Upsampling prompt tags through the host Danbooru node...");
    syncUi();
    const requestPromise = bootstrapState?.upsamplePromptWorkbenchRequest?.({
        prompt: promptText,
        negative_prompt_tags: negativePromptText,
        ban_tags: "",
      });
    if (!requestPromise || typeof requestPromise.then !== "function") {
      upsampleState.running = false;
      updateStatus("Danbooru upsampler request binding is unavailable");
      syncUi();
      return;
    }
    void requestPromise
      .then((result) => {
        if (result?.ok === false) {
          const errorDetail =
            String(result?.data?.detail ?? "").trim() ||
            String(result?.data?.availability?.detail ?? "").trim() ||
            "Danbooru upsampler request did not complete successfully";
          updateStatus(errorDetail);
          return;
        }
        const finalPrompt = String(result?.data?.final_prompt ?? "").trim();
        if (!finalPrompt) {
          updateStatus("Danbooru upsampler returned empty prompt text");
          return;
        }
        applyPromptTextToInput(finalPrompt, {
          updateEditor: true,
          statusMessage: "Applied Danbooru upsampled tags",
        });
      })
      .catch(() => {
        updateStatus("Danbooru upsampler request failed");
      })
      .finally(() => {
        upsampleState.running = false;
        syncUi();
      });
  }

  function applyPromptTextToInput(nextText, { updateEditor = true, statusMessage = "" } = {}) {
    const namespace = getActiveNamespace();
    const input = getActiveInput();
    const state = getActiveState();
    const normalizedText = String(nextText ?? "");
    state.draft_prompt = normalizedText;
    if (updateEditor) {
      editorCache.set(namespace, parsePromptTokens(normalizedText, { scope: activeScope }));
    }
    if (input) {
      input.value = normalizedText;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      queueStatePersist();
      syncUi();
    }
    if (statusMessage) {
      onStatusMessage?.(statusMessage);
      updateStatus(statusMessage);
    }
  }

  function requestAiAssistGeneration() {
    const providerId = String(configState?.ai_assist?.default_provider ?? "").trim();
    const instructionPreset = String(configState?.ai_assist?.instruction_preset ?? "").trim();
    const imageDescription = String(assistState.imageDescription ?? "").trim();
    if (!providerId) {
      updateStatus("Select a shipped AI assist provider before generating");
      return;
    }
    if (!imageDescription) {
      updateStatus("AI Assist requires an image description");
      return;
    }
    assistState.generating = true;
    updateStatus("Generating prompt with AI Assist...");
    syncUi();
    void bootstrapState
      ?.assistPromptWorkbenchRequest?.({
        provider: providerId,
        instruction_preset: instructionPreset,
        image_description: imageDescription,
        language: configState?.language ?? "en",
        theme_style: configState?.theme_style ?? "rookieui_classic",
      })
      .then((result) => {
        assistState.generatedPrompt = String(result?.data?.generated_prompt ?? "").trim();
        updateStatus(assistState.generatedPrompt ? "AI Assist generated a prompt draft" : "AI Assist returned empty prompt text");
      })
      .catch(() => {
        updateStatus("AI Assist request failed");
      })
      .finally(() => {
        assistState.generating = false;
        syncUi();
      });
  }

  function rebuildPromptFromEditor(statusMessage) {
    const namespace = getActiveNamespace();
    const tokens = ensureEditorTokens(namespace);
    const nextText = buildPromptTextFromTokens(tokens);
    const state = getActiveState();
    state.draft_prompt = nextText;
    const input = getActiveInput();
    if (input) {
      input.value = nextText;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      queueStatePersist();
      syncUi();
    }
    if (statusMessage) {
      onStatusMessage?.(statusMessage);
      updateStatus(statusMessage);
    }
  }

  function addCurrentPromptToCollection(collectionName) {
    const actionMethod =
      collectionName === "favorites"
        ? bootstrapState?.updatePromptWorkbenchFavoritesRequest
        : bootstrapState?.updatePromptWorkbenchHistoryRequest;
    const namespace = getActiveNamespace();
    const state = getActiveState();
    const promptText = state.draft_prompt || String(getActiveInput()?.value ?? "").trim();
    if (!promptText) {
      updateStatus(`No ${activeScope === "negative" ? "negative prompt" : "prompt"} text to save`);
      return;
    }
    const item = buildCollectionItem(activeScope, promptText, ensureEditorTokens(namespace));
    void actionMethod?.(namespace, "push", { item }).then((result) => {
      const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
      if (collectionName === "favorites") {
        favoritesCache.set(namespace, normalizedItems);
      } else {
        historyCache.set(namespace, normalizedItems);
      }
      updateStatus(`Saved current ${activeScope === "negative" ? "negative prompt" : "prompt"} to ${collectionName}`);
      syncUi();
    });
  }

  function applyCollectionEntry(entry) {
    applyPromptTextToInput(entry.prompt_text, {
      updateEditor: true,
      statusMessage: `Applied ${activeScope === "negative" ? "negative prompt" : "prompt"} entry`,
    });
  }

  function mutateCollection(collectionName, action, payload) {
    const namespace = getActiveNamespace();
    const actionMethod =
      collectionName === "favorites"
        ? bootstrapState?.updatePromptWorkbenchFavoritesRequest
        : bootstrapState?.updatePromptWorkbenchHistoryRequest;
    void actionMethod?.(namespace, action, payload).then((result) => {
      const normalizedItems = Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [];
      if (collectionName === "favorites") {
        favoritesCache.set(namespace, normalizedItems);
      } else {
        historyCache.set(namespace, normalizedItems);
      }
      updateStatus(`${collectionName === "favorites" ? "Favorites" : "History"} updated`);
      syncUi();
    });
  }

  function addTokenToBlacklist(tokenText) {
    const normalized = String(tokenText ?? "").trim();
    if (!normalized) {
      return;
    }
    addTokensToBlacklist([normalized]);
  }

  function addTokensToBlacklist(tokenTexts) {
    const normalizedTokens = (Array.isArray(tokenTexts) ? tokenTexts : [])
      .map((tokenText) => String(tokenText ?? "").trim())
      .filter(Boolean);
    if (!normalizedTokens.length) {
      return;
    }
    const nextEntries = Array.from(new Set([...(blacklistState.entries ?? []), ...normalizedTokens]));
    blacklistState.enabled = true;
    blacklistState.entries = nextEntries;
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      updateStatus("Prompt Workbench blacklist updated");
      syncUi();
    });
  }

  function addTokensToTranslationBlacklist(tokenTexts) {
    const normalizedTokens = (Array.isArray(tokenTexts) ? tokenTexts : [])
      .map((tokenText) => String(tokenText ?? "").trim())
      .filter(Boolean);
    if (!normalizedTokens.length) {
      return;
    }
    const nextEntries = Array.from(new Set([...(blacklistState.translation_entries ?? []), ...normalizedTokens]));
    blacklistState.translation_entries = nextEntries;
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Prompt Workbench translation blacklist updated");
      syncUi();
    });
  }

  function removeBlacklistEntry(entryText) {
    blacklistState.entries = (blacklistState.entries ?? []).filter((entry) => entry !== entryText);
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Removed blacklist entry");
      syncUi();
    });
  }

  function removeTranslationBlacklistEntry(entryText) {
    blacklistState.translation_entries = (blacklistState.translation_entries ?? []).filter((entry) => entry !== entryText);
    void bootstrapState?.updatePromptWorkbenchBlacklistRequest?.(blacklistState).then((result) => {
      if (result?.data?.blacklist) {
        Object.assign(blacklistState, result.data.blacklist);
      }
      blacklistState.translation_entries = Array.isArray(blacklistState.translation_entries) ? blacklistState.translation_entries : [];
      updateStatus("Removed translation blacklist entry");
      syncUi();
    });
  }

  function applyBlacklistFilter() {
    const tokens = ensureEditorTokens(getActiveNamespace());
    const blacklistSet = new Set((blacklistState.entries ?? []).map((entry) => String(entry).trim().toLowerCase()));
    tokens.forEach((token) => {
      token.disabled = blacklistSet.has(normalizeTokenText(token.raw_text ?? token.text).toLowerCase());
    });
    rebuildPromptFromEditor("Applied Prompt Workbench blacklist filter");
  }

  function getSelectedTokens() {
    return ensureEditorTokens(getActiveNamespace()).filter((token) => token.selected);
  }

  function mutateSelectedTokens(action) {
    const namespace = getActiveNamespace();
    const tokens = ensureEditorTokens(namespace);
    const selectedTokens = tokens.filter((token) => token.selected);
    if (!selectedTokens.length) {
      updateStatus("Select one or more prompt tokens before running a batch action");
      return;
    }
    if (action === "enable" || action === "disable") {
      selectedTokens.forEach((token) => {
        token.disabled = action === "disable";
      });
      rebuildPromptFromEditor(action === "disable" ? "Disabled selected prompt tokens" : "Enabled selected prompt tokens");
      return;
    }
    if (action === "delete") {
      editorCache.set(
        namespace,
        tokens.filter((token) => !token.selected),
      );
      rebuildPromptFromEditor("Deleted selected prompt tokens");
      return;
    }
    if (action === "copy") {
      const selectedText = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean).join(", ");
      if (navigator?.clipboard?.writeText) {
        void navigator.clipboard.writeText(selectedText);
      }
      updateStatus("Copied selected prompt tokens");
      return;
    }
    if (action === "favorite") {
      const selectedText = selectedTokens.map((token) => normalizeTokenText(token.raw_text ?? token.text)).filter(Boolean).join(", ");
      const item = buildCollectionItem(activeScope, selectedText, selectedTokens);
      void bootstrapState?.updatePromptWorkbenchFavoritesRequest?.(namespace, "push", { item }).then((result) => {
        favoritesCache.set(
          namespace,
          Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [],
        );
        updateStatus("Saved selected prompt tokens to favorites");
        syncUi();
      });
      return;
    }
    if (action === "translate") {
      translateTokenBatch(selectedTokens, String(configState.language ?? "en").trim() || "en");
      return;
    }
    if (action === "blacklist") {
      addTokensToBlacklist(selectedTokens.map((token) => token.raw_text ?? token.text));
    }
    if (action === "translation-blacklist") {
      addTokensToTranslationBlacklist(selectedTokens.map((token) => token.raw_text ?? token.text));
    }
  }

  function getInlineSuggestions() {
    const seen = new Set();
    const suggestions = [];
    const pushSuggestion = (source, label, fragment) => {
      const normalizedFragment = normalizeTokenText(fragment);
      if (!normalizedFragment || seen.has(normalizedFragment)) {
        return;
      }
      seen.add(normalizedFragment);
      suggestions.push({
        source,
        label: String(label ?? normalizedFragment),
        fragment: normalizedFragment,
      });
    };

    (favoritesCache.get(getActiveNamespace()) ?? []).slice(0, 3).forEach((entry) => {
      pushSuggestion("favorites", entry.label || "Favorite", entry.prompt_text);
    });
    (historyCache.get(getActiveNamespace()) ?? []).slice(0, 3).forEach((entry) => {
      pushSuggestion("history", entry.label || "History", entry.prompt_text);
    });
    (Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : []).slice(0, 6).forEach((entry) => {
      pushSuggestion("tagcomplete", entry?.label ?? entry?.tag, entry?.insert_token ?? entry?.tag ?? entry?.label);
    });

    return suggestions.slice(0, 8);
  }

  function renderInlineSuggestions(parent, surfaceId = "inline") {
    const suggestions = getInlineSuggestions();
    const suggestionRow = document.createElement("div");
    suggestionRow.className = "rookieui-shell__prompt-workbench-inline-suggestions";
    suggestionRow.dataset.pwUi = "inline-suggestions";
    parent.appendChild(suggestionRow);

    if (!suggestions.length) {
      appendTextElement(suggestionRow, "span", "rookieui-shell__prompt-workbench-detail", t("noInlineSuggestions"));
      return;
    }

    suggestions.forEach((suggestion, index) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-suggestion-${index}`, suggestion.label);
      button.classList.add("rookieui-shell__prompt-workbench-chip");
      button.dataset.source = suggestion.source;
      button.addEventListener("click", () => {
        appendPromptFragment(suggestion.fragment, {
          statusMessage: `Inserted ${suggestion.label}`,
        });
      });
      suggestionRow.appendChild(button);
    });
  }

  function normalizeGroupTagEntry(entry) {
    const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.english_label ?? entry?.label);
    if (!insertToken) {
      return null;
    }
    const englishLabel = normalizeTokenText(entry?.english_label ?? entry?.tag ?? insertToken) || insertToken;
    const localLabel = normalizeTokenText(entry?.local_label ?? (entry?.label && entry.label !== englishLabel ? entry.label : ""));
    return {
      ...entry,
      id: normalizeTokenText(entry?.id ?? insertToken).toLowerCase(),
      tag: normalizeTokenText(entry?.tag ?? englishLabel) || englishLabel,
      label: normalizeTokenText(entry?.label ?? localLabel ?? englishLabel) || insertToken,
      local_label: localLabel,
      english_label: englishLabel,
      insert_token: insertToken,
    };
  }

  function getNormalizedGroupTagGroups() {
    const groups = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups : [];
    return groups
      .map((group, groupIndex) => {
        const groupId = normalizeTokenText(group?.id) || `group-${groupIndex + 1}`;
        const rawSubgroups = Array.isArray(group?.subgroups) && group.subgroups.length
          ? group.subgroups
          : [
              {
                id: groupId,
                title: group?.title ?? `Group ${groupIndex + 1}`,
                tag_entries: Array.isArray(group?.tag_entries)
                  ? group.tag_entries
                  : Array.isArray(group?.tags)
                    ? group.tags.map((tag) => ({ tag, label: tag, insert_token: tag }))
                    : [],
              },
            ];
        const subgroups = rawSubgroups
          .map((subgroup, subgroupIndex) => {
            const rawEntries = Array.isArray(subgroup?.tag_entries)
              ? subgroup.tag_entries
              : Array.isArray(subgroup?.tags)
                ? subgroup.tags.map((tag) => ({ tag, label: tag, insert_token: tag }))
                : [];
            const tagEntries = rawEntries.map(normalizeGroupTagEntry).filter(Boolean);
            if (!tagEntries.length) {
              return null;
            }
            return {
              id: normalizeTokenText(subgroup?.id) || `${groupId}-${subgroupIndex + 1}`,
              title: normalizeTokenText(subgroup?.title) || normalizeTokenText(group?.title) || `Group ${groupIndex + 1}`,
              tag_entries: tagEntries,
            };
          })
          .filter(Boolean);
        if (!subgroups.length) {
          return null;
        }
        return {
          id: groupId,
          title: normalizeTokenText(group?.title) || `Group ${groupIndex + 1}`,
          subgroups,
          tag_entries: subgroups.flatMap((subgroup) => subgroup.tag_entries),
        };
      })
      .filter(Boolean);
  }

  function isGroupTagsVisible() {
    return configState?.ui_preferences?.show_group_tags !== false;
  }

  function persistGroupTagPreference(patch) {
    configState.ui_preferences = {
      ...(configState.ui_preferences ?? {}),
      ...patch,
    };
    queueConfigPersist();
  }

  function selectActiveGroupTagState(groups) {
    const preferredGroupId = normalizeTokenText(configState?.ui_preferences?.active_group_tag_group);
    const activeGroup = groups.find((group) => group.id === preferredGroupId) ?? groups[0] ?? null;
    const preferredSubgroupId = normalizeTokenText(configState?.ui_preferences?.active_group_tag_subgroup);
    const activeSubgroup = activeGroup?.subgroups.find((subgroup) => subgroup.id === preferredSubgroupId) ?? activeGroup?.subgroups[0] ?? null;
    return { activeGroup, activeSubgroup };
  }

  function hasActivePromptToken(insertToken) {
    const normalizedInsertToken = normalizeTokenText(insertToken).toLowerCase();
    return ensureEditorTokens(getActiveNamespace()).some((token) => normalizeTokenText(token.raw_text ?? token.text).toLowerCase() === normalizedInsertToken);
  }

  function toggleGroupTagEntry(entry) {
    const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.label);
    if (!insertToken) {
      return;
    }
    const normalizedInsertToken = insertToken.toLowerCase();
    const tokens = ensureEditorTokens(getActiveNamespace());
    const existingIndex = tokens.findIndex((token) => normalizeTokenText(token.raw_text ?? token.text).toLowerCase() === normalizedInsertToken);
    const label = normalizeTokenText(entry?.label) || insertToken;
    if (existingIndex >= 0) {
      tokens.splice(existingIndex, 1);
      rebuildPromptFromEditor(text("groupTagRemoved", { label }));
      syncUi();
      return;
    }
    appendPromptFragment(insertToken, {
      statusMessage: text("groupTagInserted", { label }),
    });
  }

  function renderGroupTagsBoard(parent, surfaceId = "editor") {
    const groups = getNormalizedGroupTagGroups();
    const board = document.createElement("section");
    board.className = "rookieui-shell__prompt-workbench-group-tags-board";
    board.dataset.pwUi = "group-tags-tab-board";
    parent.appendChild(board);
    const header = document.createElement("div");
    header.className = "rookieui-shell__prompt-workbench-group-tags-header";
    board.appendChild(header);
    appendTextElement(header, "h6", "rookieui-shell__prompt-workbench-pane-title", t("groupTags"));
    const toggleButton = createActionButton(
      `${idPrefix}-${surfaceId}-group-tags-visibility`,
      isGroupTagsVisible() ? t("hideGroupTags") : t("showGroupTags"),
    );
    toggleButton.classList.add("rookieui-shell__prompt-workbench-group-tags-toggle");
    toggleButton.dataset.pwUi = "group-tags-visibility-toggle";
    toggleButton.setAttribute("aria-pressed", String(isGroupTagsVisible()));
    toggleButton.addEventListener("click", () => {
      persistGroupTagPreference({ show_group_tags: !isGroupTagsVisible() });
      syncUi();
    });
    header.appendChild(toggleButton);

    if (!isGroupTagsVisible()) {
      appendTextElement(board, "p", "rookieui-shell__prompt-workbench-empty", t("groupTagsHidden"));
      return;
    }

    if (!groups.length) {
      appendTextElement(board, "p", "rookieui-shell__prompt-workbench-empty", t("noGroupTags"));
      return;
    }

    const { activeGroup, activeSubgroup } = selectActiveGroupTagState(groups);
    const activeGroupIndex = Math.max(0, groups.findIndex((group) => group.id === activeGroup?.id));
    const groupTabs = document.createElement("div");
    groupTabs.className = "rookieui-shell__prompt-workbench-group-tags-tabs";
    groupTabs.dataset.pwUi = "group-tags-group-tabs";
    board.appendChild(groupTabs);
    groups.forEach((group, groupIndex) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tags-group-${normalizeDomIdPart(group.id)}`, group.title);
      button.classList.add("rookieui-shell__prompt-workbench-group-tags-tab");
      button.dataset.pwUi = "group-tags-group-tab";
      button.dataset.active = String(group.id === activeGroup?.id);
      button.setAttribute("aria-pressed", String(group.id === activeGroup?.id));
      button.addEventListener("click", () => {
        persistGroupTagPreference({
          active_group_tag_group: group.id,
          active_group_tag_subgroup: group.subgroups[0]?.id ?? "",
        });
        syncUi();
      });
      groupTabs.appendChild(button);
    });

    const subgroupTabs = document.createElement("div");
    subgroupTabs.className = "rookieui-shell__prompt-workbench-group-tags-tabs rookieui-shell__prompt-workbench-group-tags-tabs--sub";
    subgroupTabs.dataset.pwUi = "group-tags-subgroup-tabs";
    board.appendChild(subgroupTabs);
    (activeGroup?.subgroups ?? []).forEach((subgroup) => {
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tags-subgroup-${normalizeDomIdPart(subgroup.id)}`, subgroup.title);
      button.classList.add("rookieui-shell__prompt-workbench-group-tags-tab");
      button.dataset.pwUi = "group-tags-subgroup-tab";
      button.dataset.active = String(subgroup.id === activeSubgroup?.id);
      button.setAttribute("aria-pressed", String(subgroup.id === activeSubgroup?.id));
      button.addEventListener("click", () => {
        persistGroupTagPreference({
          active_group_tag_group: activeGroup?.id ?? "",
          active_group_tag_subgroup: subgroup.id,
        });
        syncUi();
      });
      subgroupTabs.appendChild(button);
    });

    const entryGrid = document.createElement("div");
    entryGrid.className = "rookieui-shell__prompt-workbench-chip-grid rookieui-shell__prompt-workbench-group-tags-entry-grid";
    entryGrid.dataset.pwUi = "group-tags-entry-grid";
    board.appendChild(entryGrid);
    (activeSubgroup?.tag_entries ?? []).forEach((entry, entryIndex) => {
      const insertToken = normalizeTokenText(entry?.insert_token ?? entry?.tag ?? entry?.label);
      if (!insertToken) {
        return;
      }
      const label = normalizeTokenText(entry?.label) || insertToken;
      const button = createActionButton(`${idPrefix}-${surfaceId}-group-tag-${activeGroupIndex}-${entryIndex}`, "");
      button.classList.add("rookieui-shell__prompt-workbench-chip", "rookieui-shell__prompt-workbench-group-tags-entry");
      button.dataset.pwUi = "group-tags-entry";
      button.dataset.highlight = getCatalogHighlight(entry);
      button.dataset.selected = String(hasActivePromptToken(insertToken));
      button.setAttribute("aria-pressed", button.dataset.selected);
      button.title = `${activeGroup?.title ?? t("groupTags")} / ${activeSubgroup?.title ?? ""}`.trim();
      const labelStack = document.createElement("span");
      labelStack.className = "rookieui-shell__prompt-workbench-group-tags-entry-labels";
      const localLabel = normalizeTokenText(entry?.local_label);
      const englishLabel = normalizeTokenText(entry?.english_label) || insertToken;
      if (localLabel && localLabel !== englishLabel) {
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-local", localLabel);
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-en", englishLabel);
      } else {
        appendTextElement(labelStack, "span", "rookieui-shell__prompt-workbench-group-tags-entry-local", label);
      }
      button.appendChild(labelStack);
      button.addEventListener("click", () => {
        toggleGroupTagEntry(entry);
      });
      entryGrid.appendChild(button);
    });
  }

  function renderSecondaryPopover() {
    clearChildren(secondaryPopover);
    const surface = activeSecondaryPopover;
    secondaryPopover.hidden = !surface;
    secondaryPopover.dataset.activeSurface = surface;
    if (!surface) {
      return;
    }

    const title =
      surface === "settings"
        ? t("preferences")
        : surface === "favorites"
          ? t("panelFavorites")
          : surface === "append"
            ? t("append")
            : t("panelHistory");
    appendTextElement(secondaryPopover, "h6", "rookieui-shell__prompt-workbench-pane-title", title);

    if (surface === "settings") {
      [
        ["format", t("formattingAndBlacklist")],
        ["assist", t("panelAssist")],
      ].forEach(([panelId, label], index) => {
        const button = createActionButton(`${idPrefix}-settings-popover-${index}`, label);
        button.addEventListener("click", () => {
          activeSecondaryPopover = "";
          const currentState = getActiveState();
          currentState.active_panel = panelId;
          queueStatePersist();
          syncUi();
        });
        secondaryPopover.appendChild(button);
      });
      return;
    }

    if (surface === "append") {
      secondaryPopover.dataset.pwUi = "append-dropdown-popover";
      renderInlineSuggestions(secondaryPopover, "append-popover");
      renderGroupTagsBoard(secondaryPopover, "append-popover");
      return;
    }

    secondaryPopover.dataset.pwUi = "history-favorites-popovers";

    const entries = surface === "favorites"
      ? favoritesCache.get(getActiveNamespace()) ?? []
      : historyCache.get(getActiveNamespace()) ?? [];
    if (!entries.length) {
      appendTextElement(secondaryPopover, "p", "rookieui-shell__prompt-workbench-empty", `No ${surface} entries available.`);
      return;
    }

    entries.slice(0, 4).forEach((entry, index) => {
      const button = createActionButton(`${idPrefix}-${surface}-popover-${index}`, String(entry.label || entry.prompt_text || title));
      button.classList.add("rookieui-shell__prompt-workbench-popover-entry");
      button.addEventListener("click", () => {
        activeSecondaryPopover = "";
        applyCollectionEntry(entry);
      });
      secondaryPopover.appendChild(button);
    });
  }

  function renderEditorPane() {
    clearChildren(editorPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    editorPane.appendChild(heading);
    appendTextElement(
      heading,
      "h6",
      "rookieui-shell__prompt-workbench-pane-title",
      activeScope === "negative" ? t("editorNegative") : t("editorPrompt"),
    );

    const addRow = document.createElement("div");
    addRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    addRow.dataset.pwUi = "inline-add";
    editorPane.appendChild(addRow);

    const addInput = document.createElement("input");
    addInput.type = "text";
    addInput.id = `${idPrefix}-token-add`;
    addInput.className = "rookieui-shell__input";
    addInput.placeholder = "Add keyword or token";
    addRow.appendChild(addInput);

    const addButton = createActionButton(`${idPrefix}-token-add-button`, "Add Token");
    addButton.addEventListener("click", () => {
      const normalizedText = String(addInput.value ?? "").trim();
      if (!normalizedText) {
        return;
      }
      const tokens = ensureEditorTokens(getActiveNamespace());
      tokens.push(createToken(normalizedText, { scope: activeScope, orderIndex: tokens.length }));
      addInput.value = "";
      rebuildPromptFromEditor("Added prompt token");
    });
    addRow.appendChild(addButton);

    renderInlineSuggestions(editorPane);

    const translateRow = document.createElement("div");
    translateRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    editorPane.appendChild(translateRow);

    const providerSelect = document.createElement("select");
    providerSelect.id = `${idPrefix}-translation-provider`;
    providerSelect.className = "rookieui-shell__input rookieui-shell__prompt-workbench-provider-select";
    providerSelect.setAttribute("aria-label", "Prompt Workbench translation provider");
    const providerPlaceholder = document.createElement("option");
    providerPlaceholder.value = "";
    providerPlaceholder.textContent = "Translation provider";
    providerSelect.appendChild(providerPlaceholder);
    getTranslationProviders().forEach((provider) => {
      const option = document.createElement("option");
      option.value = String(provider.provider_id ?? "");
      option.textContent = String(provider.title ?? provider.provider_id ?? "");
      providerSelect.appendChild(option);
    });
    providerSelect.value = String(configState.translation?.default_provider ?? "").trim();
    providerSelect.addEventListener("change", () => {
      persistTranslationProviderSelection(providerSelect.value);
    });
    translateRow.appendChild(providerSelect);

    const translateEnglishButton = createActionButton(`${idPrefix}-translate-en`, "Translate to English");
    translateEnglishButton.addEventListener("click", () => {
      translateActivePrompt("en");
    });
    translateRow.appendChild(translateEnglishButton);

    if (normalizeLanguageCode(configState.language ?? "en").toLowerCase() !== "en") {
      const localLanguage = normalizeLanguageCode(configState.language ?? "en");
      const translateLocalButton = createActionButton(`${idPrefix}-translate-local`, `Translate to ${localLanguage}`);
      translateLocalButton.addEventListener("click", () => {
        translateActivePrompt(localLanguage);
      });
      translateRow.appendChild(translateLocalButton);
    }

    const danbooruAction = getDanbooruUpsampleAction();
    const upsampleAvailability = danbooruAction?.availability ?? {};
    const upsampleStatus = String(upsampleAvailability?.status ?? "").trim() || "host_missing";
    const upsampleRow = document.createElement("div");
    upsampleRow.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    editorPane.appendChild(upsampleRow);

    const upsampleButton = createActionButton(
      `${idPrefix}-upsample-tags`,
      upsampleState.running ? "Upsampling..." : String(danbooruAction?.title ?? "Upsample Tags"),
    );
    upsampleButton.disabled = upsampleState.running || activeScope !== "prompt" || !Boolean(danbooruAction?.available) || upsampleStatus !== "ready";
    upsampleButton.addEventListener("click", () => {
      requestDanbooruUpsample();
    });
    upsampleRow.appendChild(upsampleButton);

    const upsampleDetail = document.createElement("span");
    upsampleDetail.id = `${idPrefix}-upsample-detail`;
    upsampleDetail.className = "rookieui-shell__prompt-workbench-detail";
    upsampleDetail.textContent =
      activeScope !== "prompt"
        ? "Upsample Tags is limited to the primary prompt editor."
        : String(upsampleAvailability?.detail ?? "Danbooru upsampler host action is unavailable.");
    upsampleRow.appendChild(upsampleDetail);

    const tokens = ensureEditorTokens(getActiveNamespace());
    const selectedCount = getSelectedTokens().length;
    const batchRow = document.createElement("div");
    batchRow.className = "rookieui-shell__prompt-workbench-editor-toolbar rookieui-shell__prompt-workbench-selection-toolbar";
    batchRow.dataset.pwUi = "selection-batch-toolbar";
    batchRow.dataset.batchLayout = normalizedFixedScope ? "inline-overlay" : "panel";
    if (normalizedFixedScope && selectedCount === 0) {
      batchRow.hidden = true;
    }
    editorPane.appendChild(batchRow);

    const selectedLabel = document.createElement("span");
    selectedLabel.id = `${idPrefix}-token-selected-count`;
    selectedLabel.className = "rookieui-shell__prompt-workbench-detail";
    selectedLabel.textContent = `${selectedCount} selected`;
    batchRow.appendChild(selectedLabel);

    const batchActions = [
      ["enable", "Enable Selected"],
      ["disable", "Disable Selected"],
      ["delete", "Delete Selected"],
      ["copy", "Copy Selected"],
      ["favorite", "Favorite Selected"],
      ["translate", "Translate Selected"],
      ["blacklist", "Blacklist Selected"],
      ["translation-blacklist", "Skip Translation"],
    ];
    batchActions.forEach(([action, label]) => {
      const button = createActionButton(`${idPrefix}-token-batch-${action}`, label);
      button.disabled = selectedCount === 0;
      button.setAttribute("aria-label", `${label} prompt tokens`);
      button.addEventListener("click", () => {
        mutateSelectedTokens(action);
      });
      batchRow.appendChild(button);
    });

    const list = document.createElement("div");
    list.id = `${idPrefix}-token-list`;
    list.className = "rookieui-shell__prompt-workbench-token-list rookieui-shell__prompt-workbench-token-board";
    list.dataset.pwUi = "token-chip-board";
    list.dataset.tokenLayout = normalizedFixedScope ? "inline-tags" : "board";
    editorPane.appendChild(list);

    if (!tokens.length) {
      appendTextElement(
        list,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        "No tokens yet. Capture or add prompt text to begin editing.",
      );
      renderGroupTagsBoard(editorPane, "editor");
      return;
    }

    tokens.forEach((token, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-token rookieui-shell__prompt-workbench-token-chip";
      if (normalizedFixedScope) {
        row.classList.add("rookieui-shell__prompt-workbench-token--inline-tag");
      }
      row.dataset.pwUi = "token-chip";
      row.dataset.pwTokenUi = normalizedFixedScope ? "inline-token-tag" : "token-chip";
      row.dataset.disabled = String(token.disabled);
      row.dataset.keywordFamily = String(token.keyword_family ?? "plain");
      row.dataset.highlight = getTokenHighlight(token);
      row.draggable = true;
      row.tabIndex = 0;
      row.id = `${idPrefix}-token-${token.id}`;
      row.addEventListener("dragstart", () => {
        dragTokenId = token.id;
      });
      row.addEventListener("dragover", (event) => {
        event.preventDefault();
      });
      row.addEventListener("drop", (event) => {
        event.preventDefault();
        const draggedIndex = tokens.findIndex((entry) => entry.id === dragTokenId);
        const dropIndex = tokens.findIndex((entry) => entry.id === token.id);
        if (draggedIndex < 0 || dropIndex < 0 || draggedIndex === dropIndex) {
          return;
        }
        const [draggedToken] = tokens.splice(draggedIndex, 1);
        tokens.splice(dropIndex, 0, draggedToken);
        rebuildPromptFromEditor("Reordered prompt tokens");
      });

      const dragHandle = document.createElement("span");
      dragHandle.className = "rookieui-shell__prompt-workbench-token-handle";
      dragHandle.textContent = "::";
      row.appendChild(dragHandle);

      const selectedCheckbox = document.createElement("input");
      selectedCheckbox.type = "checkbox";
      selectedCheckbox.id = `${idPrefix}-token-select-${index}`;
      selectedCheckbox.className = "rookieui-shell__prompt-workbench-token-select";
      selectedCheckbox.setAttribute("aria-label", `Select prompt token ${index + 1}`);
      selectedCheckbox.checked = Boolean(token.selected);
      selectedCheckbox.addEventListener("change", () => {
        token.selected = selectedCheckbox.checked;
        updateStatus(token.selected ? "Selected prompt token" : "Deselected prompt token");
        syncUi();
      });
      row.appendChild(selectedCheckbox);

      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.className = "rookieui-shell__input rookieui-shell__prompt-workbench-token-input";
      valueInput.value = token.raw_text ?? token.text;
      valueInput.addEventListener("change", () => {
        updateTokenText(token, valueInput.value);
        rebuildPromptFromEditor("Edited prompt token");
      });
      row.appendChild(valueInput);

      const translatedText = String(token.translated_text ?? "").trim();
      const localLanguage = normalizeLanguageCode(configState.language ?? "en");
      const translationDetail = document.createElement("span");
      translationDetail.id = `${idPrefix}-token-translation-${index}`;
      translationDetail.className =
        "rookieui-shell__prompt-workbench-token-translation rookieui-shell__prompt-workbench-token-local-language";
      translationDetail.dataset.pwUi = "token-local-language";
      translationDetail.dataset.hasTranslation = String(Boolean(translatedText));
      translationDetail.textContent = translatedText ? `${localLanguage}: ${translatedText}` : `${localLanguage}: not translated`;
      row.appendChild(translationDetail);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-token-actions rookieui-shell__prompt-workbench-token-quick-actions";
      controls.dataset.pwUi = "token-quick-actions";
      controls.setAttribute("aria-label", "Prompt token quick actions");
      row.appendChild(controls);

      const toggleButton = createActionButton(`${idPrefix}-token-toggle-${index}`, token.disabled ? "Enable" : "Disable");
      toggleButton.addEventListener("click", () => {
        token.disabled = !token.disabled;
        rebuildPromptFromEditor(token.disabled ? "Disabled prompt token" : "Enabled prompt token");
      });
      controls.appendChild(toggleButton);

      const upButton = createActionButton(`${idPrefix}-token-up-${index}`, "Up");
      upButton.addEventListener("click", () => {
        if (index <= 0) {
          return;
        }
        [tokens[index - 1], tokens[index]] = [tokens[index], tokens[index - 1]];
        rebuildPromptFromEditor("Moved prompt token up");
      });
      controls.appendChild(upButton);

      const downButton = createActionButton(`${idPrefix}-token-down-${index}`, "Down");
      downButton.addEventListener("click", () => {
        if (index >= tokens.length - 1) {
          return;
        }
        [tokens[index], tokens[index + 1]] = [tokens[index + 1], tokens[index]];
        rebuildPromptFromEditor("Moved prompt token down");
      });
      controls.appendChild(downButton);

      const weightUpButton = createActionButton(`${idPrefix}-token-weight-up-${index}`, "Weight +");
      weightUpButton.addEventListener("click", () => {
        updateTokenText(token, adjustPromptTokenWeight(token.raw_text ?? token.text, 0.1));
        rebuildPromptFromEditor("Increased prompt token weight");
      });
      controls.appendChild(weightUpButton);

      const weightDownButton = createActionButton(`${idPrefix}-token-weight-down-${index}`, "Weight -");
      weightDownButton.addEventListener("click", () => {
        updateTokenText(token, adjustPromptTokenWeight(token.raw_text ?? token.text, -0.1));
        rebuildPromptFromEditor("Decreased prompt token weight");
      });
      controls.appendChild(weightDownButton);

      const copyButton = createActionButton(`${idPrefix}-token-copy-${index}`, "Copy");
      copyButton.addEventListener("click", () => {
        const tokenText = normalizeTokenText(token.raw_text ?? token.text);
        if (navigator?.clipboard?.writeText) {
          void navigator.clipboard.writeText(tokenText);
        }
        updateStatus("Copied prompt token");
      });
      controls.appendChild(copyButton);

      const deleteButton = createActionButton(`${idPrefix}-token-delete-${index}`, "Delete");
      deleteButton.addEventListener("click", () => {
        tokens.splice(index, 1);
        rebuildPromptFromEditor("Deleted prompt token");
      });
      controls.appendChild(deleteButton);

      const favoriteButton = createActionButton(`${idPrefix}-token-favorite-${index}`, "Favorite");
      favoriteButton.addEventListener("click", () => {
        const item = {
          label: token.raw_text ?? token.text,
          prompt_text: token.raw_text ?? token.text,
          tag_tokens: [token.raw_text ?? token.text],
          token_payloads: [serializeTokenPayload(token, index)],
        };
        void bootstrapState?.updatePromptWorkbenchFavoritesRequest?.(getActiveNamespace(), "push", { item }).then((result) => {
          favoritesCache.set(
            getActiveNamespace(),
            Array.isArray(result?.data?.items) ? result.data.items.map(normalizePromptEntry) : [],
          );
          updateStatus("Saved token to favorites");
          syncUi();
        });
      });
      controls.appendChild(favoriteButton);

      const translateButton = createActionButton(`${idPrefix}-token-translate-${index}`, "Translate");
      translateButton.addEventListener("click", () => {
        translateTokenBatch([token], String(configState.language ?? "en").trim() || "en");
      });
      controls.appendChild(translateButton);

      const blacklistButton = createActionButton(`${idPrefix}-token-blacklist-${index}`, "Blacklist");
      blacklistButton.addEventListener("click", () => {
        addTokenToBlacklist(token.raw_text ?? token.text);
      });
      controls.appendChild(blacklistButton);

      const translationBlacklistButton = createActionButton(`${idPrefix}-token-translation-blacklist-${index}`, "Skip Translate");
      translationBlacklistButton.addEventListener("click", () => {
        addTokensToTranslationBlacklist([token.raw_text ?? token.text]);
      });
      controls.appendChild(translationBlacklistButton);

      list.appendChild(row);
    });

    renderGroupTagsBoard(editorPane, "editor");
  }

  function renderCollectionPane(targetPane, collectionName) {
    clearChildren(targetPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    targetPane.appendChild(heading);
    appendTextElement(
      heading,
      "h6",
      "rookieui-shell__prompt-workbench-pane-title",
      collectionName === "favorites" ? "Favorites" : "History",
    );

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    targetPane.appendChild(toolbar);

    const saveButton = createActionButton(
      `${idPrefix}-${collectionName}-save-current`,
      collectionName === "favorites" ? "Save Current Favorite" : "Save Current Prompt",
    );
    saveButton.addEventListener("click", () => {
      addCurrentPromptToCollection(collectionName);
    });
    toolbar.appendChild(saveButton);

    const clearButton = createActionButton(`${idPrefix}-${collectionName}-clear`, "Clear");
    clearButton.addEventListener("click", () => {
      mutateCollection(collectionName, "clear", {});
    });
    toolbar.appendChild(clearButton);

    const entries = collectionName === "favorites"
      ? favoritesCache.get(getActiveNamespace()) ?? []
      : historyCache.get(getActiveNamespace()) ?? [];
    const list = document.createElement("div");
    list.className = "rookieui-shell__prompt-workbench-entry-list";
    targetPane.appendChild(list);

    if (!entries.length) {
      appendTextElement(
        list,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        `No ${collectionName} saved for this namespace yet.`,
      );
      return;
    }

    entries.forEach((entry, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-entry";
      list.appendChild(row);

      const copy = document.createElement("div");
      copy.className = "rookieui-shell__prompt-workbench-entry-copy";
      row.appendChild(copy);
      appendTextElement(copy, "strong", "rookieui-shell__prompt-workbench-entry-label", entry.label || "Saved Prompt");
      appendTextElement(copy, "p", "rookieui-shell__prompt-workbench-entry-text", entry.prompt_text);

      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-entry-actions";
      row.appendChild(controls);

      const applyButton = createActionButton(`${idPrefix}-${collectionName}-apply-${index}`, "Apply");
      applyButton.addEventListener("click", () => {
        applyCollectionEntry(entry);
      });
      controls.appendChild(applyButton);

      const removeButton = createActionButton(`${idPrefix}-${collectionName}-remove-${index}`, "Remove");
      removeButton.addEventListener("click", () => {
        mutateCollection(collectionName, "remove", { item_id: entry.id });
      });
      controls.appendChild(removeButton);

      if (collectionName === "favorites") {
        const upButton = createActionButton(`${idPrefix}-${collectionName}-up-${index}`, "Up");
        upButton.addEventListener("click", () => {
          mutateCollection(collectionName, "move_up", { item_id: entry.id });
        });
        controls.appendChild(upButton);
      }
    });
  }

  function renderCatalogPane() {
    clearChildren(catalogPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    catalogPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "Catalog and Quick Insert");

    const groups = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups : [];
    const sections = Array.isArray(catalogPayload?.prompt_library?.sections) ? catalogPayload.prompt_library.sections : [];
    const tagcompleteEntries = Array.isArray(catalogPayload?.tagcomplete?.entries) ? catalogPayload.tagcomplete.entries : [];
    const embeddings = Array.isArray(catalogPayload?.extra_networks?.embeddings) ? catalogPayload.extra_networks.embeddings : [];
    const loras = Array.isArray(catalogPayload?.extra_networks?.loras) ? catalogPayload.extra_networks.loras : [];

    const renderChipRow = (title, entries, fragmentBuilder, actionLabel = "Add") => {
      const block = document.createElement("section");
      block.className = "rookieui-shell__prompt-workbench-catalog-block";
      catalogPane.appendChild(block);
      appendTextElement(block, "h6", "rookieui-shell__prompt-workbench-pane-title", title);
      const chipGrid = document.createElement("div");
      chipGrid.className = "rookieui-shell__prompt-workbench-chip-grid";
      block.appendChild(chipGrid);
      if (!entries.length) {
        appendTextElement(
          chipGrid,
          "p",
          "rookieui-shell__prompt-workbench-empty",
          `No ${title.toLowerCase()} entries are available for this workbench profile.`,
        );
        return;
      }
      entries.forEach((entry, index) => {
        const button = createActionButton(`${idPrefix}-${title.toLowerCase().replace(/\s+/g, "-")}-${index}`, actionLabel);
        button.classList.add("rookieui-shell__prompt-workbench-chip");
        if (entry?.highlight_class) {
          button.classList.add(String(entry.highlight_class));
        }
        button.dataset.highlight = getCatalogHighlight(entry);
        if (Array.isArray(entry?.aliases) && entry.aliases.length) {
          button.title = `Aliases: ${entry.aliases.join(", ")}`;
        }
        button.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? fragmentBuilder(entry));
        button.addEventListener("click", () => {
          appendPromptFragment(fragmentBuilder(entry), {
            statusMessage: `Inserted ${String(entry?.label ?? entry?.title ?? entry?.id ?? "catalog entry")}`,
          });
        });
        chipGrid.appendChild(button);
      });
    };

    const renderNetworkSelect = (title, entries, fragmentBuilder, actionLabel = "Insert") => {
      const block = document.createElement("section");
      block.className = "rookieui-shell__prompt-workbench-catalog-block";
      catalogPane.appendChild(block);
      appendTextElement(block, "h6", "rookieui-shell__prompt-workbench-pane-title", title);
      if (!entries.length) {
        appendTextElement(
          block,
          "p",
          "rookieui-shell__prompt-workbench-empty",
          `No ${title.toLowerCase()} entries are available for this workbench profile.`,
        );
        return;
      }

      const slug = title.toLowerCase().replace(/\s+/g, "-");
      appendTextElement(
        block,
        "p",
        "rookieui-shell__prompt-workbench-empty",
        `${entries.length} ${entries.length === 1 ? "entry" : "entries"} available. Use the dropdown to keep large host inventories compact.`,
      );
      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-catalog-select-row";
      block.appendChild(controls);

      const select = document.createElement("select");
      select.id = `${idPrefix}-${slug}-select`;
      select.className = "rookieui-shell__select rookieui-shell__prompt-workbench-catalog-select";
      select.dataset.pwUi = "catalog-network-select";
      select.setAttribute("aria-label", `${title} catalog selector`);
      controls.appendChild(select);

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = `Select ${title}`;
      select.appendChild(placeholder);

      entries.forEach((entry, index) => {
        const option = document.createElement("option");
        option.id = `${idPrefix}-${slug}-option-${index}`;
        option.value = fragmentBuilder(entry);
        option.textContent = String(entry?.label ?? entry?.title ?? entry?.id ?? option.value);
        option.dataset.highlight = getCatalogHighlight(entry);
        if (Array.isArray(entry?.aliases) && entry.aliases.length) {
          option.title = `Aliases: ${entry.aliases.join(", ")}`;
        }
        select.appendChild(option);
      });

      const insertButton = createActionButton(`${idPrefix}-${slug}-${actionLabel.toLowerCase()}`, actionLabel);
      insertButton.classList.add("rookieui-shell__prompt-workbench-catalog-insert");
      insertButton.dataset.pwUi = "catalog-network-insert";
      insertButton.disabled = !select.value;
      controls.appendChild(insertButton);

      select.addEventListener("change", () => {
        insertButton.disabled = !select.value;
      });
      insertButton.addEventListener("click", () => {
        if (!select.value) {
          return;
        }
        appendPromptFragment(select.value, {
          statusMessage: `Inserted ${select.options[select.selectedIndex]?.textContent || "catalog entry"}`,
        });
      });
    };

    const tagcompleteBlock = document.createElement("section");
    tagcompleteBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    catalogPane.appendChild(tagcompleteBlock);
    appendTextElement(tagcompleteBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Tagcomplete Lookup");
    const searchInput = document.createElement("input");
    searchInput.id = `${idPrefix}-tagcomplete-search`;
    searchInput.type = "search";
    searchInput.className = "rookieui-shell__input";
    searchInput.placeholder = "Search tags, aliases, or categories";
    searchInput.setAttribute("aria-label", "Search Prompt Workbench tagcomplete catalog");
    searchInput.value = catalogSearchState.query;
    searchInput.addEventListener("input", () => {
      catalogSearchState.query = String(searchInput.value ?? "");
      syncUi();
    });
    tagcompleteBlock.appendChild(searchInput);
    const query = normalizeTokenText(catalogSearchState.query).toLowerCase();
    const filteredTagcomplete = tagcompleteEntries
      .filter((entry) => {
        if (!query) {
          return true;
        }
        const haystack = [
          entry?.tag,
          entry?.label,
          entry?.category,
          ...(Array.isArray(entry?.aliases) ? entry.aliases : []),
        ]
          .map((value) => String(value ?? "").toLowerCase())
          .join(" ");
        return haystack.includes(query);
      })
      .slice(0, 24);
    renderChipRow("Tagcomplete Matches", filteredTagcomplete, (entry) => String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""));

    groups.forEach((group, groupIndex) => {
      renderChipRow(
        String(group?.title ?? `Group ${groupIndex + 1}`),
        Array.isArray(group?.tag_entries)
          ? group.tag_entries
          : Array.isArray(group?.tags)
            ? group.tags.map((tag) => ({ id: tag, label: tag }))
            : [],
        (entry) => String(entry?.insert_token ?? entry?.tag ?? entry?.label ?? ""),
      );
    });

    sections.forEach((section, sectionIndex) => {
      const block = document.createElement("section");
      block.className = "rookieui-shell__prompt-workbench-catalog-block";
      catalogPane.appendChild(block);
      appendTextElement(
        block,
        "h6",
        "rookieui-shell__prompt-workbench-pane-title",
        String(section?.title ?? `Section ${sectionIndex + 1}`),
      );
      const list = document.createElement("div");
      list.className = "rookieui-shell__prompt-workbench-entry-list";
      block.appendChild(list);
      const entries = Array.isArray(section?.entries) ? section.entries : [];
      if (!entries.length) {
        appendTextElement(list, "p", "rookieui-shell__prompt-workbench-empty", "No prompt-library entries available.");
        return;
      }
      entries.forEach((entry, entryIndex) => {
        const row = document.createElement("div");
        row.className = "rookieui-shell__prompt-workbench-entry";
        list.appendChild(row);
        const copy = document.createElement("div");
        copy.className = "rookieui-shell__prompt-workbench-entry-copy";
        row.appendChild(copy);
        appendTextElement(copy, "strong", "rookieui-shell__prompt-workbench-entry-label", String(entry?.label ?? "Library Entry"));
        appendTextElement(copy, "p", "rookieui-shell__prompt-workbench-entry-text", String(entry?.prompt_text ?? ""));
        const controls = document.createElement("div");
        controls.className = "rookieui-shell__prompt-workbench-entry-actions";
        row.appendChild(controls);
        const appendButton = createActionButton(`${idPrefix}-library-append-${sectionIndex}-${entryIndex}`, "Append");
        appendButton.addEventListener("click", () => {
          appendPromptFragment(String(entry?.prompt_text ?? ""), {
            statusMessage: `Appended ${String(entry?.label ?? "library entry")}`,
          });
        });
        controls.appendChild(appendButton);
        const replaceButton = createActionButton(`${idPrefix}-library-replace-${sectionIndex}-${entryIndex}`, "Replace");
        replaceButton.addEventListener("click", () => {
          appendPromptFragment(String(entry?.prompt_text ?? ""), {
            replace: true,
            statusMessage: `Replaced prompt with ${String(entry?.label ?? "library entry")}`,
          });
        });
        controls.appendChild(replaceButton);
      });
    });

    renderNetworkSelect("Embeddings", embeddings, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
    renderNetworkSelect("LoRAs", loras, (entry) => String(entry?.insert_token ?? entry?.id ?? ""), "Insert");
  }

  function renderAssistPane() {
    clearChildren(assistPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    assistPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", "AI Assist and Delivery");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    assistPane.appendChild(settingsGrid);

    const renderField = (label, fieldNode) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule rookieui-shell__prompt-workbench-rule--stacked";
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      row.appendChild(fieldNode);
      settingsGrid.appendChild(row);
      return fieldNode;
    };

    const languageSelect = document.createElement("select");
    languageSelect.id = `${idPrefix}-assist-language`;
    languageSelect.className = "rookieui-shell__input";
    getLanguageOptions().forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.code ?? "en");
      option.textContent = `${String(entry?.code ?? "en")} - ${String(entry?.title ?? "English")}`;
      languageSelect.appendChild(option);
    });
    languageSelect.value = normalizeLanguageCode(configState?.language ?? "en");
    languageSelect.addEventListener("change", () => {
      setPromptWorkbenchLanguage(languageSelect.value);
    });
    renderField("Language", languageSelect);

    const themeSelect = document.createElement("select");
    themeSelect.id = `${idPrefix}-assist-theme`;
    themeSelect.className = "rookieui-shell__input";
    themeSelect.setAttribute("aria-label", "Prompt Workbench theme style");
    (themeStyleOptions.length
      ? themeStyleOptions
      : [{ id: "rookieui_classic", title: "RookieUI Classic", summary: "" }]).forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.id ?? "rookieui_classic");
      option.textContent = String(entry?.title ?? entry?.id ?? "RookieUI Classic");
      themeSelect.appendChild(option);
    });
    themeSelect.value = String(configState?.theme_style ?? "rookieui_classic");
    themeSelect.addEventListener("change", () => {
      configState.theme_style = String(themeSelect.value ?? "rookieui_classic").trim() || "rookieui_classic";
      queueConfigPersist();
    });
    renderField("Theme Style", themeSelect);

    const providerSelect = document.createElement("select");
    providerSelect.id = `${idPrefix}-assist-provider`;
    providerSelect.className = "rookieui-shell__input rookieui-shell__prompt-workbench-provider-select";
    providerSelect.setAttribute("aria-label", "Prompt Workbench AI assist provider");
    const providerPlaceholder = document.createElement("option");
    providerPlaceholder.value = "";
    providerPlaceholder.textContent = "Select AI assist provider";
    providerSelect.appendChild(providerPlaceholder);
    getAiAssistProviders().forEach((entry) => {
      const option = document.createElement("option");
      option.value = String(entry?.provider_id ?? "");
      option.textContent = String(entry?.title ?? entry?.provider_id ?? "");
      providerSelect.appendChild(option);
    });
    providerSelect.value = String(configState?.ai_assist?.default_provider ?? "");
    providerSelect.addEventListener("change", () => {
      persistAiAssistProviderSelection(providerSelect.value);
    });
    renderField("Provider", providerSelect);

    const providerDetails = getAiAssistProviders().find(
      (entry) => String(entry?.provider_id ?? "") === String(configState?.ai_assist?.default_provider ?? ""),
    );
    const providerFields = Array.isArray(providerDetails?.config_fields) ? providerDetails.config_fields : [];
    providerFields.forEach((fieldSpec) => {
      const fieldKey = String(fieldSpec?.key ?? "").trim();
      if (!fieldKey) {
        return;
      }
      const providerStore = {
        ...(configState.ai_assist?.providers ?? {}),
      };
      const providerConfig = {
        ...(providerStore[providerSelect.value] ?? {}),
      };
      const input = document.createElement("input");
      input.type = fieldSpec?.secret ? "password" : "text";
      input.id = `${idPrefix}-assist-config-${fieldKey}`;
      input.className = "rookieui-shell__input";
      input.placeholder = String(fieldSpec?.placeholder ?? "");
      input.value = String(providerConfig[fieldKey] ?? fieldSpec?.default ?? "");
      input.addEventListener("change", () => {
        const selectedProviderId = String(configState?.ai_assist?.default_provider ?? "").trim();
        if (!selectedProviderId) {
          return;
        }
        const nextProviders = {
          ...(configState.ai_assist?.providers ?? {}),
          [selectedProviderId]: {
            ...(configState.ai_assist?.providers?.[selectedProviderId] ?? {}),
            [fieldKey]: input.value,
          },
        };
        configState.ai_assist = {
          ...(configState.ai_assist ?? {}),
          providers: nextProviders,
          instruction_preset: String(configState.ai_assist?.instruction_preset ?? ""),
        };
        queueConfigPersist();
      });
      renderField(String(fieldSpec?.title ?? fieldKey), input);
    });

    const presetBlock = document.createElement("section");
    presetBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(presetBlock);
    appendTextElement(presetBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Instruction Preset");

    const presetInput = document.createElement("textarea");
    presetInput.id = `${idPrefix}-assist-preset`;
    presetInput.className = "rookieui-shell__textarea";
    presetInput.rows = 4;
    presetInput.value = String(configState?.ai_assist?.instruction_preset ?? "");
    presetInput.addEventListener("change", () => {
      configState.ai_assist = {
        ...(configState.ai_assist ?? {}),
        instruction_preset: presetInput.value,
        providers: configState.ai_assist?.providers ?? {},
      };
      queueConfigPersist();
    });
    presetBlock.appendChild(presetInput);

    const promptBlock = document.createElement("section");
    promptBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(promptBlock);
    appendTextElement(promptBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Image Description");

    const descriptionInput = document.createElement("textarea");
    descriptionInput.id = `${idPrefix}-assist-description`;
    descriptionInput.className = "rookieui-shell__textarea";
    descriptionInput.rows = 4;
    descriptionInput.placeholder = "Describe the image you want as prompt input";
    descriptionInput.value = String(assistState.imageDescription ?? "");
    descriptionInput.addEventListener("input", () => {
      assistState.imageDescription = descriptionInput.value;
    });
    promptBlock.appendChild(descriptionInput);

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    assistPane.appendChild(toolbar);

    const generateButton = createActionButton(
      `${idPrefix}-assist-generate`,
      assistState.generating ? "Generating..." : "Generate Prompt",
    );
    generateButton.disabled = assistState.generating;
    generateButton.addEventListener("click", () => {
      requestAiAssistGeneration();
    });
    toolbar.appendChild(generateButton);

    const applyButton = createActionButton(`${idPrefix}-assist-apply`, "Apply Result");
    applyButton.disabled = !String(assistState.generatedPrompt ?? "").trim();
    applyButton.addEventListener("click", () => {
      applyPromptTextToInput(assistState.generatedPrompt, {
        updateEditor: true,
        statusMessage: "Applied AI Assist prompt result",
      });
    });
    toolbar.appendChild(applyButton);

    const resultBlock = document.createElement("section");
    resultBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    assistPane.appendChild(resultBlock);
    appendTextElement(resultBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", "Generated Prompt");
    const resultInput = document.createElement("textarea");
    resultInput.id = `${idPrefix}-assist-result`;
    resultInput.className = "rookieui-shell__textarea";
    resultInput.rows = 4;
    resultInput.value = String(assistState.generatedPrompt ?? "");
    resultInput.addEventListener("input", () => {
      assistState.generatedPrompt = resultInput.value;
    });
    resultBlock.appendChild(resultInput);
  }

  async function exportWorkbenchJson(outputNode) {
    importExportState.busy = true;
    syncUi();
    const result = await bootstrapState?.exportPromptWorkbenchRequest?.();
    const payload = result?.data?.export ?? result?.data ?? {};
    importExportState.jsonText = JSON.stringify(payload, null, 2);
    if (outputNode) {
      outputNode.value = importExportState.jsonText;
    }
    importExportState.busy = false;
    updateStatus(result?.ok === false ? "Prompt Workbench export used fallback data" : t("exportReady"));
    syncUi();
  }

  async function importWorkbenchJson(inputNode) {
    const rawText = String(inputNode?.value ?? importExportState.jsonText ?? "").trim();
    let payload = null;
    try {
      payload = JSON.parse(rawText);
    } catch (_error) {
      updateStatus(t("importInvalidJson"));
      return;
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      updateStatus(t("importInvalidJson"));
      return;
    }
    importExportState.busy = true;
    syncUi();
    const result = await bootstrapState?.importPromptWorkbenchRequest?.(payload);
    importExportState.busy = false;
    updateStatus(result?.ok === false ? "Prompt Workbench import saved with fallback semantics" : t("importReady"));
    resourcesReadyPromise = null;
    resourcesLoaded = false;
    await ensureResourcesLoaded({
      statusMessage: result?.ok === false ? "Prompt Workbench import saved with fallback semantics" : t("importReady"),
    });
    syncUi();
  }

  function renderFormatPane() {
    clearChildren(formatPane);
    const heading = document.createElement("div");
    heading.className = "rookieui-shell__prompt-workbench-pane-header";
    formatPane.appendChild(heading);
    appendTextElement(heading, "h6", "rookieui-shell__prompt-workbench-pane-title", t("formattingAndBlacklist"));

    const ruleGrid = document.createElement("div");
    ruleGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    formatPane.appendChild(ruleGrid);

    const createRuleToggle = (key, label) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Boolean(configState?.formatting_rules?.[key]);
      input.addEventListener("change", () => {
        configState.formatting_rules = {
          ...configState.formatting_rules,
          [key]: input.checked,
        };
        queueConfigPersist();
      });
      row.appendChild(input);
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      ruleGrid.appendChild(row);
    };

    createRuleToggle("dedupe_commas", "Remove duplicate prompt entries");
    createRuleToggle("normalize_spacing", "Normalize spacing and comma separators");
    createRuleToggle("trim_outer_whitespace", "Trim outer whitespace");

    appendTextElement(formatPane, "h6", "rookieui-shell__prompt-workbench-pane-title", "Workbench Preferences");

    const settingsGrid = document.createElement("div");
    settingsGrid.className = "rookieui-shell__prompt-workbench-format-grid";
    formatPane.appendChild(settingsGrid);

    const createPreferenceToggle = (key, label) => {
      const row = document.createElement("label");
      row.className = "rookieui-shell__prompt-workbench-rule";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `${idPrefix}-pref-${key.replace(/_/g, "-")}`;
      input.checked = configState?.ui_preferences?.[key] !== false;
      if (key === "default_open") {
        input.checked = Boolean(configState?.ui_preferences?.default_open);
      }
      input.addEventListener("change", () => {
        configState.ui_preferences = {
          ...(configState.ui_preferences ?? {}),
          [key]: input.checked,
        };
        const state = getActiveState();
        state.active_panel = resolveVisiblePanel(state.active_panel);
        queueConfigPersist();
        syncUi();
      });
      row.appendChild(input);
      appendTextElement(row, "span", "rookieui-shell__prompt-workbench-rule-label", label);
      settingsGrid.appendChild(row);
    };

    createPreferenceToggle("default_open", "Open Prompt Workbench by default");
    createPreferenceToggle("show_history", "Show history panel");
    createPreferenceToggle("show_favorites", "Show favorites panel");

    const preferredPanelRow = document.createElement("label");
    preferredPanelRow.className = "rookieui-shell__prompt-workbench-rule rookieui-shell__prompt-workbench-rule--stacked";
    appendTextElement(preferredPanelRow, "span", "rookieui-shell__prompt-workbench-rule-label", "Preferred panel when opening");
    const preferredPanelSelect = document.createElement("select");
    preferredPanelSelect.id = `${idPrefix}-pref-preferred-panel`;
    preferredPanelSelect.className = "rookieui-shell__input";
    preferredPanelSelect.setAttribute("aria-label", "Prompt Workbench preferred panel");
    ["editor", "history", "favorites", "catalog", "assist", "format"].forEach((panelId) => {
      const option = document.createElement("option");
      option.value = panelId;
      option.textContent = panelId.charAt(0).toUpperCase() + panelId.slice(1);
      option.disabled = !isPanelVisible(panelId);
      preferredPanelSelect.appendChild(option);
    });
    preferredPanelSelect.value = resolveVisiblePanel(configState?.ui_preferences?.preferred_panel ?? "editor");
    preferredPanelSelect.addEventListener("change", () => {
      configState.ui_preferences = {
        ...(configState.ui_preferences ?? {}),
        preferred_panel: preferredPanelSelect.value,
      };
      queueConfigPersist();
      syncUi();
    });
    preferredPanelRow.appendChild(preferredPanelSelect);
    settingsGrid.appendChild(preferredPanelRow);

    const toolbar = document.createElement("div");
    toolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    formatPane.appendChild(toolbar);

    const applyFormattingButton = createActionButton(`${idPrefix}-apply-formatting`, "Apply Formatting");
    applyFormattingButton.addEventListener("click", () => {
      const formatted = formatPromptText(getActiveState().draft_prompt || getActiveInput()?.value, configState.formatting_rules);
      applyPromptTextToInput(formatted, {
        updateEditor: true,
        statusMessage: "Applied Prompt Workbench formatting rules",
      });
    });
    toolbar.appendChild(applyFormattingButton);

    const applyBlacklistButton = createActionButton(`${idPrefix}-apply-blacklist`, "Apply Blacklist");
    applyBlacklistButton.addEventListener("click", () => {
      applyBlacklistFilter();
    });
    toolbar.appendChild(applyBlacklistButton);

    const importExportBlock = document.createElement("section");
    importExportBlock.className = "rookieui-shell__prompt-workbench-catalog-block";
    formatPane.appendChild(importExportBlock);
    appendTextElement(importExportBlock, "h6", "rookieui-shell__prompt-workbench-pane-title", t("importExport"));
    const importExportInput = document.createElement("textarea");
    importExportInput.id = `${idPrefix}-import-export-json`;
    importExportInput.className = "rookieui-shell__textarea";
    importExportInput.rows = 6;
    importExportInput.value = importExportState.jsonText;
    importExportInput.addEventListener("input", () => {
      importExportState.jsonText = importExportInput.value;
    });
    importExportBlock.appendChild(importExportInput);

    const importExportToolbar = document.createElement("div");
    importExportToolbar.className = "rookieui-shell__prompt-workbench-editor-toolbar";
    importExportBlock.appendChild(importExportToolbar);
    const exportButton = createActionButton(`${idPrefix}-export-json`, t("exportJson"));
    exportButton.disabled = importExportState.busy;
    exportButton.addEventListener("click", () => {
      void exportWorkbenchJson(importExportInput);
    });
    importExportToolbar.appendChild(exportButton);

    const importButton = createActionButton(`${idPrefix}-import-json`, t("importJson"));
    importButton.disabled = importExportState.busy;
    importButton.addEventListener("click", () => {
      void importWorkbenchJson(importExportInput);
    });
    importExportToolbar.appendChild(importButton);

    const blacklistHeading = appendTextElement(
      formatPane,
      "p",
      "rookieui-shell__prompt-workbench-detail",
      blacklistState.enabled ? "Blacklist entries" : "Blacklist disabled",
    );
    blacklistHeading.id = `${idPrefix}-blacklist-heading`;

    const list = document.createElement("div");
    list.className = "rookieui-shell__prompt-workbench-entry-list";
    formatPane.appendChild(list);

    if (!(blacklistState.entries ?? []).length) {
      appendTextElement(list, "p", "rookieui-shell__prompt-workbench-empty", "No blacklist entries configured.");
    } else {
      (blacklistState.entries ?? []).forEach((entry, index) => {
        const row = document.createElement("div");
        row.className = "rookieui-shell__prompt-workbench-entry";
        list.appendChild(row);
        appendTextElement(row, "strong", "rookieui-shell__prompt-workbench-entry-label", entry);
        const controls = document.createElement("div");
        controls.className = "rookieui-shell__prompt-workbench-entry-actions";
        row.appendChild(controls);
        const removeButton = createActionButton(`${idPrefix}-blacklist-remove-${index}`, "Remove");
        removeButton.addEventListener("click", () => {
          removeBlacklistEntry(entry);
        });
        controls.appendChild(removeButton);
      });
    }

    const translationBlacklistHeading = appendTextElement(
      formatPane,
      "p",
      "rookieui-shell__prompt-workbench-detail",
      "Translation blacklist entries",
    );
    translationBlacklistHeading.id = `${idPrefix}-translation-blacklist-heading`;

    const translationList = document.createElement("div");
    translationList.className = "rookieui-shell__prompt-workbench-entry-list";
    formatPane.appendChild(translationList);

    if (!(blacklistState.translation_entries ?? []).length) {
      appendTextElement(translationList, "p", "rookieui-shell__prompt-workbench-empty", "No translation blacklist entries configured.");
      return;
    }

    (blacklistState.translation_entries ?? []).forEach((entry, index) => {
      const row = document.createElement("div");
      row.className = "rookieui-shell__prompt-workbench-entry";
      translationList.appendChild(row);
      appendTextElement(row, "strong", "rookieui-shell__prompt-workbench-entry-label", entry);
      const controls = document.createElement("div");
      controls.className = "rookieui-shell__prompt-workbench-entry-actions";
      row.appendChild(controls);
      const removeButton = createActionButton(`${idPrefix}-translation-blacklist-remove-${index}`, "Remove");
      removeButton.addEventListener("click", () => {
        removeTranslationBlacklistEntry(entry);
      });
      controls.appendChild(removeButton);
    });
  }

  function syncUi() {
    const state = getActiveState();
    state.active_panel = resolveVisiblePanel(state.active_panel);
    if ((activeSecondaryPopover === "history" && !isPanelVisible("history")) || (activeSecondaryPopover === "favorites" && !isPanelVisible("favorites"))) {
      activeSecondaryPopover = "";
    }
    const historyItems = historyCache.get(getActiveNamespace()) ?? [];
    const favoriteItems = favoritesCache.get(getActiveNamespace()) ?? [];
    const language = normalizeLanguageCode(configState?.language ?? "en");
    if (configState.language !== language) {
      configState.language = language;
    }
    const translationSurface = providersPayload?.surfaces?.translation ?? null;
    const shippedProviders = Array.isArray(translationSurface?.shipped_provider_ids)
      ? translationSurface.shipped_provider_ids.length
      : 0;
    const groupCount = Array.isArray(catalogPayload?.group_tags?.groups) ? catalogPayload.group_tags.groups.length : 0;
    const libraryCount = Array.isArray(catalogPayload?.prompt_library?.sections)
      ? catalogPayload.prompt_library.sections.length
      : 0;
    const extraNetworkCount =
      (Array.isArray(catalogPayload?.extra_networks?.embeddings) ? catalogPayload.extra_networks.embeddings.length : 0) +
      (Array.isArray(catalogPayload?.extra_networks?.loras) ? catalogPayload.extra_networks.loras.length : 0);
    const activeText = String(state.draft_prompt || getActiveInput()?.value || "");
    const activeUnitCount = countPromptUnits(activeText);

    syncLocalizedUiLabels();
    setBodyOpen(readPreferredOpenState());
    tabButtons.forEach((button, scope) => {
      button.dataset.active = String(scope === activeScope);
      button.setAttribute("aria-pressed", String(scope === activeScope));
    });
    panelButtons.forEach((button, panelId) => {
      button.hidden = !isPanelVisible(panelId);
      button.dataset.active = String(panelId === state.active_panel);
      button.setAttribute("aria-pressed", String(panelId === state.active_panel));
    });
    const quickHistoryButton = document.getElementById(`${idPrefix}-quick-history`);
    if (quickHistoryButton) {
      quickHistoryButton.hidden = !isPanelVisible("history");
      quickHistoryButton.dataset.active = String(activeSecondaryPopover === "history");
    }
    const quickFavoritesButton = document.getElementById(`${idPrefix}-quick-favorites`);
    if (quickFavoritesButton) {
      quickFavoritesButton.hidden = !isPanelVisible("favorites");
      quickFavoritesButton.dataset.active = String(activeSecondaryPopover === "favorites");
    }
    const quickSettingsButton = document.getElementById(`${idPrefix}-quick-settings`);
    if (quickSettingsButton) {
      quickSettingsButton.dataset.active = String(activeSecondaryPopover === "settings");
    }
    if (inlineToolbarNodes.counter) {
      inlineToolbarNodes.counter.textContent = `${activeUnitCount} ${activeUnitCount === 1 ? t("tagSingular") : t("tagPlural")}`;
    }
    if (inlineToolbarNodes.language) {
      inlineToolbarNodes.language.textContent = `${language} / ${activeScope === "negative" ? t("negativeScope") : t("promptScope")}`;
      inlineToolbarNodes.language.setAttribute("aria-expanded", String(languageSelectorOpen));
    }
    if (inlineToolbarNodes.historyButton) {
      inlineToolbarNodes.historyButton.hidden = !isPanelVisible("history");
      inlineToolbarNodes.historyButton.dataset.active = String(activeSecondaryPopover === "history");
      inlineToolbarNodes.historyButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "history"));
    }
    if (inlineToolbarNodes.favoritesButton) {
      inlineToolbarNodes.favoritesButton.hidden = !isPanelVisible("favorites");
      inlineToolbarNodes.favoritesButton.dataset.active = String(activeSecondaryPopover === "favorites");
      inlineToolbarNodes.favoritesButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "favorites"));
    }
    if (inlineToolbarNodes.settingsButton) {
      inlineToolbarNodes.settingsButton.dataset.active = String(activeSecondaryPopover === "settings");
      inlineToolbarNodes.settingsButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "settings"));
    }
    if (inlineToolbarNodes.appendButton) {
      inlineToolbarNodes.appendButton.dataset.active = String(activeSecondaryPopover === "append");
      inlineToolbarNodes.appendButton.setAttribute("aria-expanded", String(activeSecondaryPopover === "append"));
    }

    editorPane.hidden = state.active_panel !== "editor";
    historyPane.hidden = state.active_panel !== "history";
    favoritesPane.hidden = state.active_panel !== "favorites";
    catalogPane.hidden = state.active_panel !== "catalog";
    assistPane.hidden = state.active_panel !== "assist";
    formatPane.hidden = state.active_panel !== "format";

    updateShellThemeStyle();
    setText(summaryNodes.state, state.workbench_open ? t("persistedOpen") : t("collapsed"));
    const assistShippedProviders = Array.isArray(providersPayload?.surfaces?.ai_assist?.shipped_provider_ids)
      ? providersPayload.surfaces.ai_assist.shipped_provider_ids.length
      : 0;
    setText(
      summaryNodes.providers,
      resourcesLoaded
        ? `${shippedProviders} ${t("translateProviders")} / ${assistShippedProviders} ${t("assistProviders")} / ${language}`
        : t("lazy"),
    );
    setText(
      summaryNodes.catalogs,
      resourcesLoaded
        ? `${groupCount} ${t("groupsCount")} / ${libraryCount} ${t("sectionsCount")} / ${extraNetworkCount} ${t("networksCount")}`
        : t("lazy"),
    );
    setText(summaryNodes.history, `${historyItems.length} ${t("entries")}`);
    setText(summaryNodes.favorites, `${favoriteItems.length} ${t("entries")}`);
    setText(summaryNodes.blacklist, blacklistState.enabled ? `${(blacklistState.entries ?? []).length} ${t("blocked")}` : t("disabled"));

    setText(
      detailNodes.scope,
      text("scopeDetail", {
        scope: activeScope === "prompt" ? t("promptNamespace") : t("negativeNamespace"),
        namespace: getActiveNamespace(),
      }),
    );
    setText(detailNodes.draft, text("savedDraft", { count: countPromptUnits(state.draft_prompt) }));
    setText(detailNodes.panel, text("activePanel", { panel: state.active_panel }));

    renderEditorPane();
    renderCollectionPane(historyPane, "history");
    renderCollectionPane(favoritesPane, "favorites");
    renderCatalogPane();
    renderAssistPane();
    renderFormatPane();
    renderSecondaryPopover();
    renderLanguageSelector();
  }

  async function ensureStateLoaded() {
    if (stateReadyPromise) {
      return stateReadyPromise;
    }
    const namespacesToLoad = Object.values(namespaceMap).filter(Boolean);
    stateReadyPromise = Promise.all(
      namespacesToLoad.map(async (namespace) => {
        const result = await bootstrapState?.fetchPromptWorkbenchStateRequest?.(namespace);
        const nextState = normalizeStatePayload(
          namespace,
          result?.data?.state ?? { draft_prompt: getNamespaceInput(namespace)?.value ?? "" },
        );
        if (!nextState.draft_prompt) {
          nextState.draft_prompt = String(getNamespaceInput(namespace)?.value ?? "");
        }
        stateCache.set(namespace, nextState);
        editorCache.set(namespace, parsePromptTokens(nextState.draft_prompt, { scope: activeScope }));
      }),
    )
      .then(() => {
        if (normalizedFixedScope) {
          activeScope = normalizedFixedScope;
          return;
        }
        const promptState = stateCache.get(namespaceMap.prompt);
        const negativeState = stateCache.get(namespaceMap.negative);
        if (!promptState?.workbench_open && negativeState?.workbench_open) {
          activeScope = "negative";
        }
      })
      .finally(() => {
        syncUi();
      });
    return stateReadyPromise;
  }

  async function ensureResourcesLoaded({ statusMessage = "Prompt Workbench resources loaded" } = {}) {
    if (resourcesReadyPromise) {
      return resourcesReadyPromise;
    }
    resourcesReadyPromise = Promise.all([
      bootstrapState?.fetchPromptWorkbenchProvidersRequest?.(),
      bootstrapState?.fetchPromptWorkbenchCatalogRequest?.(normalizeLanguageCode(configState?.language ?? "en")),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchHistoryRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.prompt),
      bootstrapState?.fetchPromptWorkbenchFavoritesRequest?.(namespaceMap.negative),
      bootstrapState?.fetchPromptWorkbenchBlacklistRequest?.(),
    ])
      .then(
        ([
          providersResult,
          catalogResult,
          promptHistory,
          negativeHistory,
          promptFavorites,
          negativeFavorites,
          blacklistResult,
        ]) => {
          providersPayload = providersResult?.data ?? null;
          catalogPayload = catalogResult?.data ?? null;
          historyCache.set(
            namespaceMap.prompt,
            Array.isArray(promptHistory?.data?.items) ? promptHistory.data.items.map(normalizePromptEntry) : [],
          );
          historyCache.set(
            namespaceMap.negative,
            Array.isArray(negativeHistory?.data?.items) ? negativeHistory.data.items.map(normalizePromptEntry) : [],
          );
          favoritesCache.set(
            namespaceMap.prompt,
            Array.isArray(promptFavorites?.data?.items) ? promptFavorites.data.items.map(normalizePromptEntry) : [],
          );
          favoritesCache.set(
            namespaceMap.negative,
            Array.isArray(negativeFavorites?.data?.items) ? negativeFavorites.data.items.map(normalizePromptEntry) : [],
          );
          if (blacklistResult?.data?.blacklist) {
            Object.assign(blacklistState, blacklistResult.data.blacklist);
          }
          resourcesLoaded = true;
          updateStatus(statusMessage);
        },
      )
      .catch(() => {
        updateStatus("Prompt Workbench resources are using fallback data");
      })
      .finally(() => {
        syncUi();
      });
    return resourcesReadyPromise;
  }

  toggleButton.addEventListener("click", () => {
    void ensureStateLoaded().then(async () => {
      const state = getActiveState();
      state.workbench_open = !state.workbench_open;
      queueStatePersist();
      syncUi();
      if (state.workbench_open) {
        await ensureResourcesLoaded();
        const preferredPanel = resolveVisiblePanel(configState?.ui_preferences?.preferred_panel ?? state.active_panel);
        if (preferredPanel !== state.active_panel) {
          state.active_panel = preferredPanel;
          queueStatePersist();
          syncUi();
        }
        onStatusMessage?.("Opened Prompt Workbench");
      } else {
        onStatusMessage?.("Collapsed Prompt Workbench");
      }
    });
  });

  function shouldIgnoreWorkbenchHotkey(event) {
    const target = event?.target;
    if (!target || !shell.contains(target)) {
      return true;
    }
    const tagName = String(target.tagName ?? "").toLowerCase();
    if (["input", "select", "textarea"].includes(tagName)) {
      return true;
    }
    return Boolean(target.isContentEditable);
  }

  shell.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activeSecondaryPopover && shell.contains(event.target)) {
      event.preventDefault();
      activeSecondaryPopover = "";
      syncUi();
      updateStatus("Closed Prompt Workbench popover");
      return;
    }
    if (event.key === "Escape" && languageSelectorOpen && shell.contains(event.target)) {
      event.preventDefault();
      closeLanguageSelector({ focusTrigger: true });
      updateStatus("Closed Prompt Workbench language selector");
      return;
    }
    if (shouldIgnoreWorkbenchHotkey(event)) {
      return;
    }
    const isModifier = Boolean(event.ctrlKey || event.metaKey);
    if (event.key === "Delete") {
      event.preventDefault();
      mutateSelectedTokens("delete");
      return;
    }
    if (isModifier && String(event.key).toLowerCase() === "c") {
      event.preventDefault();
      mutateSelectedTokens("copy");
      return;
    }
    if (isModifier && String(event.key).toLowerCase() === "t") {
      event.preventDefault();
      mutateSelectedTokens("translate");
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (!languageSelectorOpen) {
      return;
    }
    const target = event.target;
    if (inlineToolbarNodes.language?.contains(target) || inlineToolbarNodes.languageSelector?.contains(target)) {
      return;
    }
    closeLanguageSelector({ focusTrigger: true });
  });

  const repositionLanguageSelector = () => {
    if (languageSelectorOpen) {
      placeLanguageSelector();
    }
  };
  globalThis?.addEventListener?.("resize", repositionLanguageSelector, { passive: true });
  globalThis?.addEventListener?.("scroll", repositionLanguageSelector, { passive: true, capture: true });

  Object.entries(namespaceMap).forEach(([scope, namespace]) => {
    if (normalizedFixedScope && scope !== normalizedFixedScope) {
      return;
    }
    const input = inputMap[scope];
    if (!input || !namespace) {
      return;
    }
    input.addEventListener("input", () => {
      const cachedState =
        stateCache.get(namespace) ?? normalizeStatePayload(namespace, { draft_prompt: String(input.value ?? "") });
      cachedState.draft_prompt = String(input.value ?? "");
      stateCache.set(namespace, cachedState);
      const nextTokens = parsePromptTokens(cachedState.draft_prompt, { scope });
      editorCache.set(namespace, nextTokens);
      queueAutoHistoryCapture(namespace, scope, cachedState.draft_prompt, nextTokens);
      queueStatePersist(namespace);
      if (scope === activeScope) {
        syncUi();
      }
    });
  });

  void ensureStateLoaded();
  syncUi();
  return {
    element: shell,
    async openWorkbench() {
      await ensureStateLoaded();
      const state = getActiveState();
      if (!state.workbench_open) {
        state.workbench_open = true;
        queueStatePersist();
      }
      await ensureResourcesLoaded();
      syncUi();
    },
  };
}
