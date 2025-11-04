// === SIDEBAR TOGGLE ===
function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("active");
}

// === CLOSE SIDEBAR WHEN CLICKING OUTSIDE ===
document.addEventListener("click", function (event) {
  const sidebar = document.getElementById("sidebar");
  const menuIcon = document.querySelector(".menu-icon");
  
  // If sidebar is open and clicked area is outside both sidebar and icon → close it
  if (sidebar.classList.contains("active") &&
      !sidebar.contains(event.target) &&
      !menuIcon.contains(event.target)) {
    sidebar.classList.remove("active");
  }
});

// === SEARCH FUNCTION WITH POPUP ===
function performSearch() {
  const query = document.getElementById("searchInput").value.trim().toLowerCase();
  const popup = document.getElementById("popup");
  const popupMessage = document.getElementById("popup-message");

  if (!query) return; // Don’t trigger on empty input

  const pages = {
    about: "/about",
    migration: "/migration",
    users: "/users",
    home: "/"
  };

  if (pages[query]) {
    window.location.href = pages[query];
  } else {
    popupMessage.textContent = `No results found for "${query}".`;
    popup.style.display = "flex";
  }
}

// === CLOSE POPUP ===
function closePopup() {
  document.getElementById("popup").style.display = "none";
}
document.getElementById("popup-close").addEventListener("click", closePopup);

// === EVENT LISTENERS ===
document.querySelector(".menu-icon").addEventListener("click", toggleSidebar);
document.getElementById("searchButton").addEventListener("click", performSearch);