"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from 'next/navigation';

type State = "idle" | "launching" | "room_created" | "error";

type SpriteOption = {
  value: string;
  label: string;
};

const spriteOptions: SpriteOption[] = [
  { value: "parkingmeter", label: "Parking meter" },
  { value: "parkingmeter_banana", label: "Minion meter" },
  { value: "robot", label: "Robot" },
];

export default function App() {
  const [state, setState] = useState<State>("idle");
  const [room, setRoom] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>(process.env.SYSTEM_PROMPT || "You are a friendly chatbot.");
  const [spriteFolderName, setSpriteFolderName] = useState<string>(spriteOptions[0].value);
  const [name, setName] = useState<string>(process.env.BOT_NAME || "Chatbot");
  const [currentLink, setCurrentLink] = useState<string>("");
  const [copySuccess, setCopySuccess] = useState<string>("");

  const searchParams = useSearchParams();

  useEffect(() => {
    const promptParam = searchParams.get('prompt');
    const spriteParam = searchParams.get('sprite');
    const nameParam = searchParams.get('name');

    if (promptParam) {
      setSystemPrompt(decodeURIComponent(promptParam));
    }
    if (spriteParam) {
      const decodedSprite = decodeURIComponent(spriteParam);
      if (spriteOptions.some(option => option.value === decodedSprite)) {
        setSpriteFolderName(decodedSprite);
      }
    }
    if (nameParam) {
      setName(decodeURIComponent(nameParam));
    }
  }, [searchParams]);

  const generateLink = useCallback(() => {
    if (typeof window !== 'undefined') {
      const baseUrl = window.location.origin + window.location.pathname;
      const params = new URLSearchParams();
      if (systemPrompt) params.set('prompt', encodeURIComponent(systemPrompt));
      if (spriteFolderName) params.set('sprite', encodeURIComponent(spriteFolderName));
      if (name) params.set('name', encodeURIComponent(name));
      return `${baseUrl}?${params.toString()}`;
    }
    return '';
  }, [systemPrompt, spriteFolderName, name]);

  useEffect(() => {
    setCurrentLink(generateLink());
  }, [generateLink]);

  const copyToClipboard = (text: string, successMessage: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopySuccess(successMessage);
      setTimeout(() => setCopySuccess(""), 3000);
    }).catch(err => {
      console.error('Failed to copy: ', err);
      setCopySuccess("Failed to copy");
    });
  };

  async function launchBot() {
    setState("launching");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

    try {
      const response = await fetch("/start_bot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          system_prompt: systemPrompt,
          sprite_folder: spriteFolderName || undefined,
          name: name
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const { room_url } = await response.json();

      setRoom(room_url);
      setState("room_created");
    } catch (error) {
      console.error("Error launching bot:", error);
      if (error instanceof Error && error.name === 'AbortError') {
        console.error("Request timed out");
      }
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const [errorMessage, setErrorMessage] = useState<string>("");

  if (state === "error") {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <div className="bg-white p-6 rounded-lg shadow-xl max-w-2xl w-full">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-700 mb-4">
            An error occurred while launching the bot:
          </p>
          <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-60 mb-4">
            {errorMessage || "Unknown error occurred. Please try again later."}
          </pre>
          <button
            onClick={() => setState("idle")}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Back to Configuration
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-full bg-gray-100 p-4">
      {state === "idle" && (
        <div className="w-full max-w-4xl bg-white p-8 rounded-lg shadow-md space-y-6">
          <h1 className="text-3xl font-bold text-center mb-6">Bot Configuration</h1>
          <div className="flex justify-end">
            <button
              onClick={() => copyToClipboard(currentLink, "Configuration copied!")}
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105"
            >
              Copy this configuration
            </button>
          </div>
          <div>
            <label htmlFor="spriteSelect" className="block text-sm font-medium text-gray-700 mb-1">
              Appearance
            </label>
            <select
              id="spriteSelect"
              value={spriteFolderName}
              onChange={(e) => setSpriteFolderName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            >
              {spriteOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter bot name..."
            />
          </div>
          <div>
            <label htmlFor="systemPrompt" className="block text-sm font-medium text-gray-700 mb-1">
              System Prompt
            </label>
            <textarea
              id="systemPrompt"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full h-32 p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter system prompt..."
            />
          </div>
          <div className="flex justify-center">
            <button
              onClick={launchBot}
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 ease-in-out transform hover:scale-105"
            >
              Launch Bot
            </button>
          </div>
        </div>
      )}
      {state === "launching" && (
        <div className="text-center">
          <p className="text-xl mb-4">Launching bot...</p>
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      )}
      {state === "room_created" && (
        <div className="text-center space-y-6 bg-white p-8 rounded-lg shadow-md">
          <h2 className="text-2xl font-bold text-green-600 mb-4">Room created successfully!</h2>
          <button
            onClick={() => window.open(room || "#", "_blank", "noopener,noreferrer")}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 ease-in-out transform hover:scale-105"
          >
            Open Room
          </button>
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => room && copyToClipboard(room, "Room link copied!")}
              className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105"
            >
              Copy link to room
            </button>
            <button
              onClick={() => copyToClipboard(currentLink, "Configuration copied!")}
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105"
            >
              Copy this configuration
            </button>
            <button
              onClick={() => window.open(currentLink, "_blank", "noopener,noreferrer")}
              className="bg-yellow-500 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out transform hover:scale-105"
            >
              Open Configuration
            </button>
          </div>
        </div>
      )}
      {copySuccess && (
        <div className="fixed bottom-4 right-4 bg-green-500 text-white py-2 px-4 rounded shadow-lg">
          {copySuccess}
        </div>
      )}
    </div>
  );
}
