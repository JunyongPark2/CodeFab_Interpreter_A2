if (window.mermaid) {
  mermaid.initialize({
    startOnLoad: true,
    theme: "base",
    fontFamily: "IBM Plex Mono, monospace",
    themeVariables: {
      primaryColor: "#eef2fb",
      primaryTextColor: "#1c1f24",
      primaryBorderColor: "#2554c7",
      lineColor: "#5b6270",
      secondaryColor: "#f5f6f8",
      tertiaryColor: "#ffffff",
      actorBkg: "#eef2fb",
      actorBorder: "#2554c7",
      actorTextColor: "#1c1f24",
      signalColor: "#5b6270",
      signalTextColor: "#1c1f24",
      labelBoxBkgColor: "#eef2fb",
      labelBoxBorderColor: "#2554c7",
      loopTextColor: "#1c1f24",
      noteBkgColor: "#f5f6f8",
      noteBorderColor: "#dfe2e7",
      fontSize: "13px",
    },
  });
}

const track = document.querySelector(".track");
const slides = Array.from(document.querySelectorAll(".slide"));
const links = Array.from(document.querySelectorAll(".nav__link"));
const progressCurrent = document.querySelector(".progress__current");
const progressTotal = document.querySelector(".progress__total");

const linkTargets = links.map((link) => {
  const target = document.querySelector(link.dataset.target);
  return slides.indexOf(target);
});

let index = 0;

progressTotal.textContent = slides.length;

function goTo(i) {
  index = Math.max(0, Math.min(slides.length - 1, i));
  track.style.transform = `translateX(-${index * 100}vw)`;

  // Highlight the nav link for the current group: the last link whose
  // target slide index is at or before the current slide.
  let activeLink = -1;
  linkTargets.forEach((targetIndex, li) => {
    if (targetIndex <= index) activeLink = li;
  });
  links.forEach((link, li) => link.classList.toggle("is-active", li === activeLink));

  progressCurrent.textContent = index + 1;
}

links.forEach((link, li) => {
  link.addEventListener("click", () => goTo(linkTargets[li]));
});

window.addEventListener("keydown", (e) => {
  const forwardKeys = ["Space", "ArrowRight", "ArrowDown", "PageDown"];
  const backKeys = ["ArrowLeft", "ArrowUp", "PageUp"];

  if (forwardKeys.includes(e.code)) {
    e.preventDefault();
    goTo(index + 1);
  } else if (backKeys.includes(e.code)) {
    e.preventDefault();
    goTo(index - 1);
  }
});

goTo(0);
