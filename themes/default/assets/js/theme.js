// Toggle theme

const getTheme = window.localStorage && window.localStorage.getItem("theme");
const themeToggle = document.querySelector(".theme-toggle");
const isDark = getTheme === "dark";

if (getTheme !== null) {
  document.body.classList.toggle("dark-theme", isDark);
}

const updateImgs = (currentTheme) => {
  const imgs = document.getElementsByClassName("img-toggle");
  for (let i = 0; i < imgs.length; i++) {
    const src = imgs[i].src;
    imgs[i].src = currentTheme === "dark" ? src.replace("light", "dark") : src.replace("dark", "light");
  }
}

updateImgs(getTheme);

themeToggle.addEventListener("click", () => {
  // toggle theme
  document.body.classList.toggle("dark-theme");

  window.localStorage && window.localStorage.setItem("theme", document.body.classList.contains("dark-theme") ? "dark" : "light");
  
  // update images src
  updateImgs(window.localStorage && window.localStorage.getItem("theme"));
});
