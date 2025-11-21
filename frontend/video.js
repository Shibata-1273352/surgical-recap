// frontend/video.js
const BACKEND_BASE = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const videoName = params.get("name");

  const titleEl = document.getElementById("video-page-title");
  const videoEl = document.getElementById("video-player");
  const sourceEl = document.getElementById("video-source");

  if (!videoName) {
    titleEl.textContent = "No video specified";
    return;
  }

  titleEl.textContent = videoName;

  // Set video source
  const videoUrl =
    BACKEND_BASE + "/static/videos/" + encodeURIComponent(videoName);
  sourceEl.src = videoUrl;
  videoEl.load();

  setupComments(videoName, videoEl);
  setupChat(videoName, videoEl);
});

/* -------- COMMENTS WITH CRUD + REPLY + LIKE/UNLIKE ---------- */

function setupComments(videoName, videoEl) {
  const commentsList = document.getElementById("comments-list");
  const form = document.getElementById("comment-form");
  const input = document.getElementById("comment-input");

  // Track liked comments locally so we can toggle like/unlike
  const storageKey = `likedComments_${videoName}`;
  let likedSet = new Set();
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) likedSet = new Set(JSON.parse(raw));
  } catch {
    likedSet = new Set();
  }

  function saveLikedSet() {
    try {
      localStorage.setItem(storageKey, JSON.stringify([...likedSet]));
    } catch {
      // ignore
    }
  }

  // --------- HTTP helpers ---------

  async function fetchComments() {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(videoName)}/comments`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.comments || [];
  }

  async function postComment({ text, timestamp, parentId = null }) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(videoName)}/comments`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          timestamp,
          parent_id: parentId,
        }),
      }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
  }

  async function updateComment(id, newText) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/comments/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newText }),
      }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
  }

  async function deleteComment(id) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/comments/${encodeURIComponent(id)}`,
      {
        method: "DELETE",
      }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
  }

  async function likeComment(id) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/comments/${encodeURIComponent(id)}/like`,
      { method: "POST" }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    try {
      return await res.json(); // {status, likes}
    } catch {
      return null;
    }
  }

  async function unlikeComment(id) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/comments/${encodeURIComponent(id)}/unlike`,
      { method: "POST" }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    try {
      return await res.json(); // {status, likes}
    } catch {
      return null;
    }
  }

  // --------- render logic ---------

  function buildCommentTree(comments) {
    const byParent = new Map();
    comments.forEach((c) => {
      const key = c.parent_id ?? null;
      if (!byParent.has(key)) byParent.set(key, []);
      byParent.get(key).push(c);
    });
    return byParent;
  }

  function renderCommentsTree(byParent) {
    commentsList.innerHTML = "";
    const roots = byParent.get(null) || [];
    if (!roots.length) {
      commentsList.textContent = "No comments yet.";
      return;
    }
    roots.forEach((c) => renderSingleComment(c, byParent, commentsList, false));
  }

  function renderSingleComment(comment, byParent, container, isReply) {
    const div = document.createElement("div");
    div.className = "comment-item";
    if (isReply) div.classList.add("comment-reply");

    const ts = formatTime(comment.timestamp ?? 0);

    const tsLink = document.createElement("a");
    tsLink.href = "#";
    tsLink.className = "timestamp-link";
    tsLink.textContent = `[${ts}]`;
    tsLink.addEventListener("click", (e) => {
      e.preventDefault();
      videoEl.currentTime = comment.timestamp;
      videoEl.play();
    });

    const textSpan = document.createElement("span");
    textSpan.className = "comment-text";
    textSpan.textContent = `: ${comment.text}`;

    const actionsDiv = document.createElement("div");
    actionsDiv.className = "comment-actions";

    const replyBtn = document.createElement("button");
    replyBtn.type = "button";
    replyBtn.className = "comment-btn";
    replyBtn.textContent = "Reply";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "comment-btn";
    editBtn.textContent = "Edit";

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "comment-btn";
    deleteBtn.textContent = "Delete";

    const likeBtn = document.createElement("button");
    likeBtn.type = "button";
    likeBtn.className = "comment-like-btn";

    const currentLikes = comment.likes ?? 0;
    likeBtn.textContent = `♥ ${currentLikes}`;

    if (likedSet.has(comment.id)) {
      likeBtn.classList.add("liked");
    }

    const headerrow = document.createElement("div");
    headerrow.className = "comment-headerrow";
    headerrow.appendChild(tsLink);
    headerrow.appendChild(textSpan);
    headerrow.appendChild(likeBtn);

    actionsDiv.appendChild(replyBtn);
    actionsDiv.appendChild(editBtn);
    actionsDiv.appendChild(deleteBtn);
   

    const replyFormContainer = document.createElement("div");

    div.appendChild(headerrow);
    div.appendChild(actionsDiv);
    div.appendChild(replyFormContainer);
    container.appendChild(div);

    // --- handlers ---

    replyBtn.addEventListener("click", () => {
      // toggle inline reply box
      if (replyFormContainer.firstChild) {
        replyFormContainer.innerHTML = "";
        return;
      }

      const ta = document.createElement("textarea");
      ta.rows = 2;
      ta.placeholder = "Write a reply…";
      ta.style.width = "100%";
      ta.style.marginTop = "4px";

      const submit = document.createElement("button");
      submit.type = "button";
      submit.textContent = "Post reply";
      submit.className = "comment-btn";
      submit.style.marginTop = "4px";

      replyFormContainer.appendChild(ta);
      replyFormContainer.appendChild(submit);

      submit.addEventListener("click", async () => {
        const text = ta.value.trim();
        if (!text) return;

        const timestamp = videoEl.currentTime || comment.timestamp || 0;

        try {
          await postComment({
            text,
            timestamp,
            parentId: comment.id,
          });
          replyFormContainer.innerHTML = "";
          await loadComments();
        } catch (err) {
          console.error("Error posting reply:", err);
          alert("Error posting reply. See console for details.");
        }
      });
    });

    editBtn.addEventListener("click", async () => {
      const currentText = comment.text || "";
      const newText = window.prompt("Edit comment:", currentText);
      if (newText === null) return; // cancelled
      const trimmed = newText.trim();
      if (!trimmed) return;

      try {
        await updateComment(comment.id, trimmed);
        await loadComments();
      } catch (err) {
        console.error("Error editing comment:", err);
        alert("Error editing comment. See console for details.");
      }
    });

    deleteBtn.addEventListener("click", async () => {
      const ok = window.confirm(
        "Delete this comment and all its replies?"
      );
      if (!ok) return;

      try {
        await deleteComment(comment.id);
        // also forget any liked state in this thread
        likedSet.delete(comment.id);
        saveLikedSet();
        await loadComments();
      } catch (err) {
        console.error("Error deleting comment:", err);
        alert("Error deleting comment. See console for details.");
      }
    });

    likeBtn.addEventListener("click", async () => {
      try {
        let updated;
        if (likedSet.has(comment.id)) {
          // unlike
          updated = await unlikeComment(comment.id);
          likedSet.delete(comment.id);
          likeBtn.classList.remove("liked");
        } else {
          // like
          updated = await likeComment(comment.id);
          likedSet.add(comment.id);
          likeBtn.classList.add("liked");
        }
        saveLikedSet();

        if (updated && typeof updated.likes === "number") {
          likeBtn.textContent = `♥ ${updated.likes}`;
        } else {
          // fallback: just adjust by +/-1
          const current = parseInt(
            likeBtn.textContent.replace(/[^\d]/g, "") || "0",
            10
          );
          const delta = likedSet.has(comment.id) ? 1 : -1;
          likeBtn.textContent = `♥ ${Math.max(0, current + delta)}`;
        }
      } catch (err) {
        console.error("Error liking/unliking comment:", err);
        alert("Error updating like. See console for details.");
      }
    });

    // children / replies
    const children = byParent.get(comment.id) || [];
    children.forEach((child) =>
      renderSingleComment(child, byParent, container, true)
    );
  }

  async function loadComments() {
    commentsList.innerHTML = "Loading comments…";
    try {
      const comments = await fetchComments();
      const byParent = buildCommentTree(comments);
      renderCommentsTree(byParent);
    } catch (err) {
      console.error("Error loading comments:", err);
      commentsList.textContent = "Error loading comments.";
    }
  }

  // main comment form (top-level)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    const timestamp = videoEl.currentTime || 0;

    try {
      await postComment({ text, timestamp, parentId: null });
      input.value = "";
      await loadComments();
    } catch (err) {
      console.error("Error adding comment:", err);
      alert("Error adding comment. See console for details.");
    }
  });

  loadComments();
}

/* -------- CHATBOT (unchanged, just wired to /api/chat) ---------- */

/* -------- CHATBOT WITH PERSISTENT CHATS & TABS ---------- */

function setupChat(videoName, videoEl) {
  const chatWindow = document.getElementById("chat-window");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatTabs = document.getElementById("chat-tabs");
  const newChatBtn = document.getElementById("new-chat-btn");

  if (!chatWindow || !chatForm || !chatInput || !chatTabs || !newChatBtn) {
    return;
  }

  let currentChatId = null;
  let chatsMeta = []; // [{id, title, created_at, num_messages}]

  function clearChatWindow() {
    chatWindow.innerHTML = "";
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `chat-message ${role}`;
    div.textContent = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function renderChatTabs() {
    chatTabs.innerHTML = "";

    if (!chatsMeta.length) {
      const span = document.createElement("span");
      span.textContent = "No chats yet";
      chatTabs.appendChild(span);
      return;
    }

    chatsMeta.forEach((chat) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chat-tab-btn";
      btn.textContent = chat.title;
      if (chat.id === currentChatId) {
        btn.classList.add("active");
      }
      btn.addEventListener("click", () => {
        if (chat.id === currentChatId) return;
        currentChatId = chat.id;
        loadChatHistory(chat.id);
      });
      chatTabs.appendChild(btn);
    });
  }

  async function fetchChatsList() {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(videoName)}/chats`
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    const data = await res.json();
    return data.chats || [];
  }

  async function createNewChat() {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(videoName)}/chats`,
      {
        method: "POST",
      }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    return await res.json(); // {id, created_at}
  }

  async function fetchChatHistory(chatId) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/chats/${encodeURIComponent(chatId)}`
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    const data = await res.json();
    return data.messages || [];
  }

  async function sendChatMessage(chatId, userText, timestamp) {
    const res = await fetch(
      `${BACKEND_BASE}/api/videos/${encodeURIComponent(
        videoName
      )}/chats/${encodeURIComponent(chatId)}/message`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          timestamp,
        }),
      }
    );
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t}`);
    }
    const data = await res.json();
    return data; // {reply, messages?, chat_meta?}
  }

  async function loadChatHistory(chatId) {
    clearChatWindow();
    appendMessage(
      "bot",
      "Loading previous messages for this chat..."
    );
    try {
      const messages = await fetchChatHistory(chatId);
      clearChatWindow();
      if (!messages.length) {
        appendMessage(
          "bot",
          "New chat started. Ask me anything about this video!"
        );
      } else {
        messages.forEach((m) => {
          appendMessage(m.role, m.text);
        });
      }
      renderChatTabs();
    } catch (err) {
      console.error("Error loading chat history:", err);
      clearChatWindow();
      appendMessage("bot", "Error loading this chat.");
    }
  }

  async function initChatArea() {
    try {
      chatsMeta = await fetchChatsList();
    } catch (err) {
      console.error("Error fetching chat list:", err);
      appendMessage("bot", "Error loading chats from server.");
      return;
    }

    if (!chatsMeta.length) {
      // create first chat
      try {
        const created = await createNewChat();
        currentChatId = created.id;
        chatsMeta = [
          {
            id: created.id,
            title: "Chat 1",
            created_at: created.created_at,
            num_messages: 0,
          },
        ];
        renderChatTabs();
        clearChatWindow();
        appendMessage(
          "bot",
          "Hi! This is your first chat for this video. Ask me anything about it!"
        );
      } catch (err) {
        console.error("Error creating initial chat:", err);
        appendMessage("bot", "Could not create an initial chat.");
      }
    } else {
      // load the most recent chat
      currentChatId = chatsMeta[0].id;
      renderChatTabs();
      await loadChatHistory(currentChatId);
    }
  }

  newChatBtn.addEventListener("click", async () => {
  // If current chat has no stored messages, don't create a new one
  if (currentChatId) {
    const currentMeta = chatsMeta.find((c) => c.id === currentChatId);
    const currentCount = currentMeta?.num_messages ?? 0;

    if (currentCount === 0) {
      // Stay on this chat; optionally give a small hint
      appendMessage(
        "bot",
        "This chat is still empty. Send a message first before starting a new chat."
      );
      return;
    }
  }

  // Current chat has messages → it's ok to create a new one
  try {
    const created = await createNewChat();
    const idx = chatsMeta.length + 1;
    const meta = {
      id: created.id,
      title: created.title,
      created_at: created.created_at,
      num_messages: 0,
    };
    chatsMeta.unshift(meta);
    currentChatId = created.id;
    renderChatTabs();
    clearChatWindow();
    appendMessage(
      "bot",
      "Started a new chat. Context is cleared for this conversation."
    );
  } catch (err) {
    console.error("Error creating new chat:", err);
    alert("Could not start a new chat. See console for details.");
  }
});


  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    if (!currentChatId) {
      alert("No active chat. Try clicking 'New chat'.");
      return;
    }

    const timestamp = videoEl.currentTime || 0;

    appendMessage("user", text);
    chatInput.value = "";

    try {
      const data = await sendChatMessage(currentChatId, text, timestamp);
      const reply = data.reply || "(no reply)";
      appendMessage("bot", reply);

      // optional: update meta if backend sends it
      if (data.chat_meta && data.chat_meta.id === currentChatId) {
        const idx = chatsMeta.findIndex((c) => c.id === currentChatId);
        if (idx !== -1) {
          chatsMeta[idx] = {
            ...chatsMeta[idx],
            ...data.chat_meta,
          };
        }
      }
      renderChatTabs();
    } catch (err) {
      console.error("Chat error:", err);
      appendMessage("bot", "Error talking to the chatbot backend.");
    }
  });

  // Initialize: load chats from backend or create a new one
  initChatArea();
}


/* -------- UTIL ---------- */

function formatTime(seconds) {
  const s = Math.floor(seconds % 60);
  const m = Math.floor(seconds / 60);
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return `${mm}:${ss}`;
}
