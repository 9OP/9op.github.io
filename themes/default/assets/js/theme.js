// Toggle theme

const getTheme = window.localStorage && window.localStorage.getItem("theme");
const themeToggle = document.querySelector(".theme-toggle");
const isDark = getTheme === "dark";

if (getTheme !== null) {
  document.body.classList.toggle("dark-theme", isDark);
}

themeToggle.addEventListener("click", () => {
  const theme = document.body.classList.contains("dark-theme") ? "dark" : "light";

  // toggle theme
  document.body.classList.toggle("dark-theme");

  // update images src
  const imgs = document.getElementsByClassName("img-toggle");
  for (let i = 0; i < imgs.length; i++) {
    const src = imgs[i].src;
    imgs[i].src = theme === "light" ? src.replace("light", "dark") : src.replace("dark", "light");
  }

  window.localStorage && window.localStorage.setItem("theme", theme);
});
