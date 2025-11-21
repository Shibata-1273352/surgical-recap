// frontend/main.js
const BACKEND_BASE = "http://localhost:8000";

let videos = [];

document.addEventListener("DOMContentLoaded", () => {
  loadVideos();
  setupUpload();
});

async function loadVideos() {
  try {
    const res = await fetch(`${BACKEND_BASE}/api/videos`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    videos = await res.json();

    const list = document.getElementById("video-list");
    list.innerHTML = "";

    if (!videos.length) {
      list.textContent = "No videos uploaded yet.";
      return;
    }

    videos.forEach((v) => {
      const item = document.createElement("div");
      item.className = "video-list-item";

      const info = document.createElement("div");
      info.className = "video-info";

      const title = document.createElement("div");
      title.className = "video-title";
      title.textContent = v.title;

      const desc = document.createElement("div");
      desc.className = "video-desc";
      desc.textContent = v.description || "";

      info.appendChild(title);
      info.appendChild(desc);

      const actions = document.createElement("div");
      actions.className = "video-actions";

      const playBtn = document.createElement("button");
      playBtn.textContent = "Play";
      playBtn.className = "btn-primary";
      playBtn.onclick = () => {
        // Go to video detail page with ?name=<filename>
        window.location.href =
          "video.html?name=" + encodeURIComponent(v.title);
      };

      const deleteBtn = document.createElement("button");
      deleteBtn.textContent = "Delete";
      deleteBtn.className = "btn-danger";
      deleteBtn.onclick = async () => {
      const confirmed = window.confirm(
        `Are you sure you want to delete "${v.title}"?`
    );
      if (!confirmed) return;
        try {
          const res = await fetch(
            `${BACKEND_BASE}/api/videos/${encodeURIComponent(v.title)}`,
            { method: "DELETE" }
        );

        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text}`);
        }

        // Refresh the list
        await loadVideos();
        } catch (err) {
        console.error("Error deleting video:", err);
        alert("Error deleting video. See console for details.");
        }
    };

      actions.appendChild(playBtn);
      actions.appendChild(deleteBtn);

      item.appendChild(info);
      item.appendChild(actions);

      list.appendChild(item);
    });
  } catch (err) {
    console.error("Error loading videos:", err);
    const list = document.getElementById("video-list");
    list.textContent =
      "Error loading videos. Check that the backend is running.";
  }
}

function setupUpload() {
  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("video-file");
  const statusEl = document.getElementById("upload-status");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    statusEl.textContent = "";

    const file = fileInput.files[0];
    if (!file) {
      statusEl.textContent = "Please select a video to upload.";
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    statusEl.textContent = "Uploading…";

    try {
      const res = await fetch(`${BACKEND_BASE}/api/videos/uploadLocal`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed: ${res.status} ${text}`);
      }

      const data = await res.json();
      statusEl.textContent = data.message || "Upload complete.";

      fileInput.value = "";
      await loadVideos();
    } catch (err) {
      console.error("Upload error:", err);
      statusEl.textContent =
        "Error uploading video. See console for details.";
    }
  });
}
