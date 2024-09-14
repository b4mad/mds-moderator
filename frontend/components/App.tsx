"use client";

import React, { useState } from "react";
import { useDaily } from "@daily-co/daily-react";
import Setup from "./Setup";
import Story from "./Story";

type State =
  | "idle"
  | "launching"
  | "room_created"
  | "connecting"
  | "connected"
  | "started"
  | "finished"
  | "error";

export default function Call() {
  const daily = useDaily();

  const [state, setState] = useState<State>("idle");
  const [room, setRoom] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);

  async function launchBot() {
    setState("launching");

    try {
      const response = await fetch("/start_bot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const { room_url, token } = await response.json();

      setRoom(room_url);
      setToken(token);
      setState("room_created");
    } catch (error) {
      console.error("Error launching bot:", error);
      setState("error");
    }
  }

  async function joinRoom() {
    if (!daily || !room || !token) return;

    setState("connecting");

    try {
      await daily.join({
        url: room,
        token: token,
        videoSource: false,
        startAudioOff: true,
      });

      setState("connected");
      daily.setLocalAudio(false);
      setState("started");
    } catch (error) {
      console.error("Error joining room:", error);
      setState("error");
    }
  }

  async function leave() {
    await daily?.leave();
    setState("finished");
  }

  if (state === "error") {
    return (
      <div className="flex items-center mx-auto">
        <p className="text-red-500 font-semibold bg-white px-4 py-2 shadow-xl rounded-lg">
          An error occurred. Please try again later.
        </p>
      </div>
    );
  }

  if (state === "started") {
    return <Story handleLeave={() => leave()} />;
  }

  return (
    <div className="flex flex-col items-center space-y-4">
      {state === "idle" && (
        <button
          onClick={launchBot}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Launch Bot
        </button>
      )}
      {state === "launching" && <p>Launching bot...</p>}
      {state === "room_created" && (
        <>
          <p>Room created successfully!</p>
          <a
            href={room || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-700 underline"
          >
            {room}
          </a>
          <button
            onClick={joinRoom}
            className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
          >
            Join Room
          </button>
        </>
      )}
      {(state === "connecting" || state === "connected") && <p>Connecting to room...</p>}
      {state === "finished" && (
        <p>Session finished. Refresh the page to start a new session.</p>
      )}
    </div>
  );
}
