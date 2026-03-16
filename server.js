const express = require('express');
const app = express();
app.use(express.json());

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

const BOT_TOKEN  = '8681523916:AAEE2mpKPsdBk3UDG-qVyFDdkJIazKP_EBg';
const MY_CHAT_ID = '7571759883';

app.post('/submit', async (req, res) => {
    console.log('Data received:', req.body);

const name  = req.body.name;
const type  = req.body.type;
const email = req.body.email;
const phone = req.body.phone;

  const message = `
New form submission!
--------------------
Type:  ${type}
Data:  ${name}
  `.trim();

  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: MY_CHAT_ID,
      text: message
    })
  });

  res.json({ ok: true });

});

app.use(express.static(__dirname));

app.listen(3000, () => {
  console.log('Server is running! Waiting for submissions...');
});