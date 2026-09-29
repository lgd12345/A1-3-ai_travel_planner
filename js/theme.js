const THEME_STORAGE_KEY = "tripai-theme";

const themeToggleButton = document.getElementById("themeToggle");

const systemPrefersDark = window.matchMedia(
  "(prefers-color-scheme: dark)"
);

function getSavedTheme() {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);

  if (
    savedTheme === "light" ||
    savedTheme === "dark"
  ) {
    return savedTheme;
  }

  return null;
}

function getPreferredTheme() {
  const savedTheme = getSavedTheme();

  if (savedTheme) {
    return savedTheme;
  }

  return systemPrefersDark.matches
    ? "dark"
    : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;

  updateThemeButton(theme);
}

function updateThemeButton(theme) {
  if (!themeToggleButton) {
    return;
  }

  const isDark = theme === "dark";

  themeToggleButton.setAttribute(
    "aria-label",
    isDark
      ? "라이트 모드로 전환"
      : "다크 모드로 전환"
  );

  themeToggleButton.setAttribute(
    "title",
    isDark
      ? "라이트 모드"
      : "다크 모드"
  );

  const icon = themeToggleButton.querySelector(
    "[aria-hidden='true']"
  );

  if (icon) {
    icon.textContent = isDark
      ? "☀"
      : "☾";
  }
}

function toggleTheme() {
  const currentTheme =
    document.documentElement.dataset.theme ||
    getPreferredTheme();

  const nextTheme =
    currentTheme === "dark"
      ? "light"
      : "dark";

  localStorage.setItem(
    THEME_STORAGE_KEY,
    nextTheme
  );

  applyTheme(nextTheme);
}

function handleSystemThemeChange(event) {
  /*
   * 사용자가 직접 테마를 선택했다면
   * 시스템 테마가 바뀌어도 사용자 설정을 우선합니다.
   */
  if (getSavedTheme()) {
    return;
  }

  applyTheme(
    event.matches
      ? "dark"
      : "light"
  );
}

function initializeTheme() {
  applyTheme(
    getPreferredTheme()
  );

  if (themeToggleButton) {
    themeToggleButton.addEventListener(
      "click",
      toggleTheme
    );
  }

  systemPrefersDark.addEventListener(
    "change",
    handleSystemThemeChange
  );
}

initializeTheme();