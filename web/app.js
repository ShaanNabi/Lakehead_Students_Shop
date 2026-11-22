// this file runs in the browser and builds the whole shop page
// it talks to the flask api with fetch, the same urls the java app uses

const $ = (id) => document.getElementById(id);   // shortcut for finding an element by its id

let me = null;           // the logged in user, or null if nobody is logged in
let listings = [];       // the listings showing in the table right now
let categories = [];     // the categories from the server, used by the listing form
let chatTimer = null;    // timer that keeps an open chat up to date

const dialog = $("dialog");   // the one popup every dialog reuses


// talking to the server

// sends a request to flask and always gives back { ok, status, data }
async function api(method, url, body) {
  const options = { method, headers: {} };                       // start with the method and no headers
  if (body !== undefined) {                                      // only send a body when we have one
    options.headers["Content-Type"] = "application/json";        // tell flask the body is json
    options.body = JSON.stringify(body);                         // turn the object into text
  }
  try {
    const res = await fetch(url, options);                       // send it
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }  // the reply might not be json
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { error: "Could not reach the server." } };   // network problem
  }
}

// if flask says we are not logged in, show the login popup and return true
function authExpired(res) {
  if (res.status !== 401) return false;                          // only care about 401
  me = null;                                                     // forget the old user
  updateAccount();
  loginDialog("Your session expired. Please log in again.");
  return true;
}


// small helpers

// builds an html element, text always goes in as plain text so nobody can sneak code in
function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") node.textContent = value;                           // plain text
    else if (key === "class") node.className = value;                       // css class
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);   // onclick, onsubmit and so on
    else node.setAttribute(key, value);                                     // everything else
  }
  for (const kid of kids) {
    if (kid !== null && kid !== undefined && kid !== false) node.append(kid);   // skip empty kids
  }
  return node;
}

const money = (cents) => "$" + (cents / 100).toFixed(2);            // 4500 becomes $45.00
const niceCondition = (c) => c.replaceAll("_", " ");                // like_new becomes like new
const setStatus = (text) => { $("status").textContent = text; };    // the line at the bottom

// one row in a two column form, label then field
function field(label, input) {
  return [el("label", { for: input.id, text: label }), input];
}


// popups

// shows the popup with a title, some content and a row of buttons
// a button is { label, onclick } or { label, form } where form is the id of a form to submit
function openDialog(title, body, buttons) {
  stopChat();                                                        // an old chat should stop refreshing
  const bar = el("div", { class: "buttons" });
  for (const b of buttons) {
    const button = el("button", { type: b.form ? "submit" : "button", text: b.label });
    if (b.form) button.setAttribute("form", b.form);                 // submits that form even though it sits outside it
    else button.addEventListener("click", b.onclick);
    bar.append(button);
  }
  dialog.replaceChildren(el("h2", { text: title }), body, bar);
  if (!dialog.open) dialog.showModal();                              // opens it on top of the page
}

const closeDialog = () => dialog.close();

function stopChat() {
  clearInterval(chatTimer);                                          // stop the refresh timer
  chatTimer = null;
}
dialog.addEventListener("close", stopChat);                          // closing the popup stops the chat refresh too


// account stuff

// shows login buttons or the name of whoever is logged in
function updateAccount() {
  const box = $("account");
  if (me) {
    box.replaceChildren(
      "Signed in as " + me.first_name + " " + me.last_name,
      el("button", { type: "button", text: "Log out", onclick: logout })
    );
  } else {
    box.replaceChildren(
      el("button", { type: "button", text: "Log in", onclick: () => loginDialog() }),
      el("button", { type: "button", text: "Sign up", onclick: () => signupDialog() })
    );
  }
  $("messagesBtn").hidden = !me;                                     // only logged in people have messages
}

async function logout() {
  await api("POST", "/api/logout");
  me = null;
  updateAccount();
  if (dialog.open) closeDialog();
  setStatus("Logged out.");
}

// note is optional text shown above the form, then is what to do after logging in
function loginDialog(note, then) {
  const email = el("input", { id: "loginEmail", type: "email", required: "", autocomplete: "username" });
  const password = el("input", { id: "loginPassword", type: "password", required: "", autocomplete: "current-password" });
  const error = el("p", { class: "error" });

  const form = el("form", {
    id: "loginForm",
    class: "form",
    onsubmit: async (e) => {
      e.preventDefault();                                            // stop the page from reloading
      const res = await api("POST", "/api/login", { email: email.value.trim(), password: password.value });
      if (!res.ok) { error.textContent = (res.data && res.data.error) || "Could not log in."; return; }
      me = res.data.user;                                            // remember who logged in
      updateAccount();
      closeDialog();
      if (then) then();                                              // carry on with what they were doing
    },
  }, ...field("Email", email), ...field("Password", password));

  openDialog("Log in", el("div", {}, note ? el("p", { text: note }) : null, form, error), [
    { label: "Cancel", onclick: closeDialog },
    { label: "Sign up", onclick: () => signupDialog(note, then) },
    { label: "Log in", form: "loginForm" },
  ]);
}

function signupDialog(note, then) {
  const first = el("input", { id: "suFirst", type: "text", required: "", autocomplete: "given-name" });
  const last = el("input", { id: "suLast", type: "text", required: "", autocomplete: "family-name" });
  const email = el("input", { id: "suEmail", type: "email", required: "", autocomplete: "username" });
  const password = el("input", { id: "suPassword", type: "password", required: "", minlength: "8", autocomplete: "new-password" });
  const error = el("p", { class: "error" });

  const form = el("form", {
    id: "signupForm",
    class: "form",
    onsubmit: async (e) => {
      e.preventDefault();
      const res = await api("POST", "/api/register", {
        first_name: first.value.trim(),
        last_name: last.value.trim(),
        email: email.value.trim(),
        password: password.value,
      });
      if (!res.ok) { error.textContent = (res.data && res.data.error) || "Could not sign up."; return; }
      me = res.data.user;                                            // signing up also logs you in
      updateAccount();
      closeDialog();
      if (then) then();
    },
  }, ...field("First name", first), ...field("Last name", last),
     ...field("Email", email), ...field("Password", password));

  const hint = el("p", { class: "hint", text: "Use your @lakeheadu.ca email. Password needs at least 8 characters." });
  openDialog("Sign up", el("div", {}, note ? el("p", { text: note }) : null, hint, form, error), [
    { label: "Cancel", onclick: closeDialog },
    { label: "Log in instead", onclick: () => loginDialog(note, then) },
    { label: "Create account", form: "signupForm" },
  ]);
}


// the table of listings

async function loadListings() {
  const text = $("search").value.trim();                             // what they typed in the search bar
  $("searchBtn").disabled = true;                                    // no spamming while it loads
  $("refreshBtn").disabled = true;
  setStatus("Loading listings...");

  const res = await api("GET", "/api/listings" + (text ? "?q=" + encodeURIComponent(text) : ""));

  $("searchBtn").disabled = false;
  $("refreshBtn").disabled = false;

  if (!res.ok || !Array.isArray(res.data)) {                         // something went wrong
    setStatus("Could not load listings. Is the server running?");
    return;
  }

  listings = res.data;
  const rows = $("rows");
  rows.replaceChildren();                                            // clear the old rows
  for (const item of listings) {
    const row = el("tr", { tabindex: "0", onclick: () => showListing(item) },
      el("td", { text: item.title }),
      el("td", { text: money(item.price_cents) }),
      el("td", { text: item.category_name }),
      el("td", { text: niceCondition(item.condition) }),
      el("td", { text: item.seller_name })
    );
    row.addEventListener("keydown", (e) => { if (e.key === "Enter") showListing(item); });   // keyboard users can open it too
    rows.append(row);
  }
  setStatus(listings.length + " listing(s) found. Click a listing for details.");
}

// popup with the listing details
function showListing(item) {
  const isOwner = me !== null && me.id === item.seller_id;           // is this your own listing

  const text = [
    "Item: " + item.title,
    "Price: " + money(item.price_cents),
    "Category: " + item.category_name,
    "Condition: " + niceCondition(item.condition),
    "Seller: " + item.seller_name,
    "",
    "Description:",
    item.description || "",
  ].join("\n");

  const buttons = [{ label: "Close", onclick: closeDialog }];
  if (isOwner) {                                                     // owners can edit and delete
    buttons.push({ label: "Edit Listing", onclick: () => listingForm(item) });
    buttons.push({ label: "Delete Listing", onclick: () => deleteListing(item) });
  } else {                                                           // everyone else can message the seller
    buttons.push({ label: "Message Seller", onclick: () => messageSeller(item) });
  }
  openDialog("Listing details", el("pre", { class: "details", text }), buttons);
}


// creating, editing and deleting listings

// the same form is used for creating (no item) and editing (item given)
function listingForm(item) {
  const editing = item !== undefined;

  const title = el("input", { id: "lfTitle", type: "text", required: "", maxlength: "120" });
  const description = el("textarea", { id: "lfDescription", rows: "4" });
  const price = el("input", { id: "lfPrice", type: "number", required: "", min: "0", step: "0.01", inputmode: "decimal" });
  const category = el("select", { id: "lfCategory" });
  for (const c of categories) category.append(el("option", { value: c.id, text: c.name }));
  const condition = el("select", { id: "lfCondition" });
  for (const [value, label] of [["new", "New"], ["like_new", "Like new"], ["used", "Used"], ["fair", "Fair"]]) {
    condition.append(el("option", { value, text: label }));
  }
  const error = el("p", { class: "error" });

  if (editing) {                                                     // fill the form with the current values
    title.value = item.title;
    description.value = item.description || "";
    price.value = (item.price_cents / 100).toFixed(2);
    category.value = item.category_id;
    condition.value = item.condition;
  } else {
    condition.value = "used";                                        // used is the default, same as the server
  }

  const form = el("form", {
    id: "listingForm",
    class: "form",
    onsubmit: async (e) => {
      e.preventDefault();
      const data = {
        title: title.value.trim(),
        description: description.value.trim(),
        price: Number(price.value),
        category_id: Number(category.value),
        condition: condition.value,
      };
      if (!data.title) { error.textContent = "Please enter a title."; return; }
      if (!(data.price >= 0)) { error.textContent = "Please enter a valid price."; return; }

      const res = editing
        ? await api("PUT", "/api/listings/" + item.id, data)         // edit an existing listing
        : await api("POST", "/api/listings", data);                  // post a new one
      if (authExpired(res)) return;
      if (!res.ok) { error.textContent = (res.data && res.data.error) || "Could not save the listing."; return; }

      closeDialog();
      await loadListings();                                          // show the change in the table
      setStatus(editing ? "Listing updated successfully!" : "Listing created successfully!");
    },
  }, ...field("Item Title", title), ...field("Description:", description), ...field("Price ($):", price),
     ...field("Category:", category), ...field("Condition:", condition));

  openDialog(editing ? "Edit Listing" : "Create Listing", el("div", {}, form, error), [
    { label: "Cancel", onclick: closeDialog },
    { label: editing ? "Save Changes" : "Post Listing", form: "listingForm" },
  ]);
}

async function deleteListing(item) {
  if (!confirm("Are you sure you want to delete this listing?")) return;   // ask first
  const res = await api("DELETE", "/api/listings/" + item.id);
  if (authExpired(res)) return;
  closeDialog();
  if (!res.ok) { setStatus("Could not delete listing."); return; }
  await loadListings();
  setStatus("Listing deleted successfully.");
}


// messaging

function messageSeller(item) {
  if (!me) {                                                         // need an account to message
    loginDialog("Log in to message the seller.", () => messageSeller(item));
    return;
  }
  chatDialog({ listingId: item.id, title: "Chat with " + item.seller_name + " about " + item.title });
}

// opts has title and either listingId (start or find a chat for that listing) or convoId (open that chat)
function chatDialog(opts) {
  let convoId = opts.convoId || null;                                // null until the chat exists

  const log = el("div", { class: "chat-log" });
  const error = el("p", { class: "error" });
  const input = el("input", { id: "chatInput", type: "text", maxlength: "1000", autocomplete: "off" });
  const form = el("form", { id: "chatForm", class: "chat-form", onsubmit: send }, input);

  // shows the messages in the log
  function draw(messages) {
    log.replaceChildren();
    if (messages.length === 0) {
      log.append(el("p", { class: "hint", text: "Send a message to start the conversation." }));
    }
    for (const m of messages) {
      const mine = m.sender_id === me.id;
      log.append(el("p", { text: (mine ? "You" : m.sender_name) + ": " + m.body }));
    }
    log.scrollTop = log.scrollHeight;                                // jump to the newest message
  }

  async function refresh() {
    if (!convoId) return;                                            // nothing to load yet
    const res = await api("GET", "/api/conversations/" + convoId + "/messages");
    if (res.ok) draw(res.data);
  }

  function startTimer() {
    if (!chatTimer) chatTimer = setInterval(refresh, 5000);          // check for new messages every 5 seconds
  }

  async function send(e) {
    e.preventDefault();
    const body = input.value.trim();
    if (!body) return;                                               // ignore empty messages
    error.textContent = "";
    const url = convoId
      ? "/api/conversations/" + convoId + "/messages"                // chat already exists
      : "/api/listings/" + opts.listingId + "/messages";             // first message starts the chat
    const res = await api("POST", url, { body });
    if (authExpired(res)) return;
    if (!res.ok) { error.textContent = (res.data && res.data.error) || "Could not send the message."; return; }
    input.value = "";
    if (!convoId) { convoId = res.data.conversation_id; startTimer(); }   // the server tells us the new chat id
    await refresh();
  }

  openDialog(opts.title, el("div", {}, log, error, form), [
    { label: "Close", onclick: closeDialog },
    { label: "Send", form: "chatForm" },
  ]);
  draw([]);

  (async () => {                                                     // look for an existing chat in the background
    if (!convoId) {
      const res = await api("GET", "/api/conversations");
      if (res.ok) {
        const found = res.data.find((c) => c.listing_id === opts.listingId && c.buyer_id === me.id);
        if (found) convoId = found.id;
      }
    }
    await refresh();
    if (convoId && dialog.open) startTimer();                        // only keep refreshing if the popup is still open
  })();
}

// inbox with every chat you are in, so sellers can read and reply too
async function messagesDialog() {
  const res = await api("GET", "/api/conversations");
  if (authExpired(res)) return;

  const list = el("div", { class: "inbox" });
  if (!res.ok) {
    list.append(el("p", { class: "hint", text: "Could not load messages." }));
  } else if (res.data.length === 0) {
    list.append(el("p", { class: "hint", text: "No messages yet." }));
  } else {
    for (const c of res.data) {
      const other = c.buyer_id === me.id ? c.seller_name : c.buyer_name;   // the other person in the chat
      list.append(el("button", {
        type: "button",
        class: "inbox-row",
        onclick: () => chatDialog({ convoId: c.id, title: "Chat with " + other + " about " + c.listing_title }),
      }, el("strong", { text: c.listing_title }),
         el("span", { text: "with " + other }),
         el("span", { class: "hint", text: c.last_message || "" })));
    }
  }
  openDialog("Messages", list, [{ label: "Close", onclick: closeDialog }]);
}


// hooking everything up when the page loads

$("searchBtn").addEventListener("click", loadListings);
$("search").addEventListener("keydown", (e) => { if (e.key === "Enter") loadListings(); });   // enter also searches
$("refreshBtn").addEventListener("click", () => { $("search").value = ""; loadListings(); });  // refresh clears the search
$("createBtn").addEventListener("click", () => {
  if (me) listingForm();
  else loginDialog("Log in to post a listing.", () => listingForm());
});
$("messagesBtn").addEventListener("click", messagesDialog);

async function start() {
  const [meRes, catRes] = await Promise.all([api("GET", "/api/me"), api("GET", "/api/categories")]);
  if (meRes.ok) me = meRes.data.user;                                // already logged in from earlier
  if (catRes.ok) categories = catRes.data.sort((a, b) => a.id - b.id);   // same order as the java dropdown
  updateAccount();
  loadListings();
}
start();
