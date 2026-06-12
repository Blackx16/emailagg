// ─── Simulated Data ──────────────────────────────────────────────────────────

const mockEmails = [
  {
    sender: "Netflix Security",
    senderEmail: "info@account.netflix.com",
    mailbox: "nico.melendez2009@outlook.com",
    subject: "Netflix: your sign-in code",
    body: "Enter this code to sign in: 5722. This code will expire in 15 minutes.",
    otp: "5722",
    time: "Just Now"
  },
  {
    sender: "Google Account Security",
    senderEmail: "no-reply@accounts.google.com",
    mailbox: "my.google.user@gmail.com",
    subject: "Google Verification Code: 498302",
    body: "Your Google verification code is 498302. Do not share it with anyone else.",
    otp: "498302",
    time: "2m ago"
  },
  {
    sender: "Microsoft Accounts",
    senderEmail: "account-security-noreply@accountprotection.microsoft.com",
    mailbox: "user_outlook@outlook.com",
    subject: "Microsoft Account Password Reset Code",
    body: "To reset your password, use code 88294. If you didn't request this, ignore.",
    otp: "88294",
    time: "10m ago"
  },
  {
    sender: "GitHub Support",
    senderEmail: "noreply@github.com",
    mailbox: "developer_git@gmail.com",
    subject: "[GitHub] Security Alert: New login detected",
    body: "A login was detected from a new IP address on your account. Review details...",
    otp: null,
    time: "1h ago"
  }
];

// ─── Interactive Phone Mockup ────────────────────────────────────────────────

function simulateEmail(index) {
  // 1. Toggle active class on list items
  const items = document.querySelectorAll('.email-item');
  items.forEach((item, idx) => {
    if (idx === index) {
      item.classList.add('active');
      // Remove unread badge if present
      const badge = item.querySelector('.email-badge-unread');
      if (badge) badge.remove();
    } else {
      item.classList.remove('active');
    }
  });

  const email = mockEmails[index];
  const alertBox = document.getElementById('simulatedAlert');
  const alertText = document.getElementById('alertText');
  const alertTime = document.getElementById('alertTime');

  // 2. Hide and show with animation
  alertBox.classList.add('hidden');
  
  // Force reflow
  void alertBox.offsetWidth;

  // 3. Set text content
  let contentHtml = `
    🤖 <b>New Email Alert</b><br>
    📬 <b>Mailbox:</b> <code>${email.mailbox}</code><br>
    📧 <b>From:</b> ${email.sender} &lt;${email.senderEmail}&gt;<br>
    📝 <b>Subject:</b> ${email.subject}<br>
  `;

  if (email.otp) {
    contentHtml += `
      🔑 <b>OTP Code:</b> <code>${email.otp}</code><br>
      <div class="otp-copy-box">
        <span>Code: ${email.otp}</span>
        <button class="otp-copy-btn" onclick="copyMockOtp('${email.otp}', this)">Copy</button>
      </div>
    `;
  } else {
    contentHtml += `
      📄 <b>Snippet:</b> <i>"${email.body.substring(0, 70)}..."</i>
    `;
  }

  alertText.innerHTML = contentHtml;
  alertTime.innerText = email.time;
  alertBox.classList.remove('hidden');

  // Scroll to bottom of chat area
  const chatArea = document.getElementById('chatArea');
  chatArea.scrollTop = chatArea.scrollHeight;
}

function copyMockOtp(code, button) {
  navigator.clipboard.writeText(code).then(() => {
    button.innerText = "Copied!";
    button.style.background = "#059669";
    setTimeout(() => {
      button.innerText = "Copy";
      button.style.background = "#10b981";
    }, 2000);
  });
}

// Initialize Netflix email simulation on load
window.addEventListener('load', () => {
  simulateEmail(0);
});

// ─── Interactive Rules Simulator ─────────────────────────────────────────────

let logCounter = 1;

function writeLog(text, type = "muted") {
  const logBox = document.getElementById('terminalLog');
  const dateStr = new Date().toLocaleTimeString();
  const line = document.createElement('span');
  line.className = `log-line text-${type}`;
  line.innerHTML = `[${dateStr}] [line:${logCounter++}] ${text}`;
  logBox.appendChild(line);
  
  // Keep logs capped at 12 items
  while (logBox.children.length > 12) {
    logBox.removeChild(logBox.firstChild);
  }
  
  logBox.scrollTop = logBox.scrollHeight;
}

async function runRuleTest() {
  const condition = document.getElementById('ruleCondition').value;
  
  writeLog("evaluating rules match engine...", "info");
  await sleep(600);
  
  if (condition === "none") {
    writeLog("evaluating globally scoped rules...", "info");
    await sleep(400);
    writeLog("match found! Rule matches ANY email", "success");
    await sleep(400);
    writeLog("forwarding email using Gmail API from user account...", "info");
    await sleep(500);
    writeLog("Gmail API returned 200 OK. Forward complete!", "success");
    return;
  }
  
  if (condition === "netflix") {
    writeLog("evaluating rule (Subject ~ 'Netflix')...", "info");
    await sleep(400);
    writeLog("comparing against subject: 'Netflix: your sign-in code'", "info");
    await sleep(400);
    writeLog("match found! 'Netflix' matches Subject contains filter", "success");
    await sleep(500);
    writeLog("OAuth token fetch successful. Forwarding from user's Outlook account...", "info");
    await sleep(500);
    writeLog("Microsoft Graph API returned 202 Accepted. Forward complete!", "success");
    return;
  }
  
  if (condition === "google") {
    writeLog("evaluating rule (Subject ~ 'Google')...", "info");
    await sleep(400);
    writeLog("comparing against subject: 'Netflix: your sign-in code'", "info");
    await sleep(400);
    writeLog("mismatch. Skipping globally scoped rule Google...", "warning");
    return;
  }
  
  if (condition === "github") {
    writeLog("evaluating rule (From Domain ~ 'github.com')...", "info");
    await sleep(400);
    writeLog("comparing against from address: 'info@account.netflix.com'", "info");
    await sleep(400);
    writeLog("mismatch. Skipping globally scoped rule github.com...", "warning");
    return;
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
