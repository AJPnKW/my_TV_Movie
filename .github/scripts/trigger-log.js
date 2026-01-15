import fetch from "node-fetch";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).send("Method Not Allowed");
  }

  const entry = await req.text();

  const response = await fetch(
    "https://api.github.com/repos/AJPnKW/my_TV_Movie/dispatches",
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${process.env.LOGGING_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        event_type: "log_visit",
        client_payload: { entry },
      }),
    }
  );

  if (!response.ok) {
    return res.status(500).send("Failed to dispatch event");
  }

  return res.status(200).send("Logged");
}
