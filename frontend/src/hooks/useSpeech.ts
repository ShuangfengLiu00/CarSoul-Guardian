import { useCallback, useEffect, useRef, useState } from "react";

interface UseSpeechOptions {
  /** Speech recognition language (BCP-47). */
  lang?: string;
  /** Text-to-speech language. */
  ttsLang?: string;
  /** Keep recognizing after a pause (push-to-talk should stay false). */
  continuous?: boolean;
  /** Emit interim (non-final) results while speaking. */
  interimResults?: boolean;
}

/**
 * Vehicle-screen voice interaction hook.
 *
 * Wraps the browser Web Speech API into a single push-to-talk + auto-narrate
 * controller tailored for the in-car large screen:
 *   - `startListening / stopListening` drive a microphone button.
 *   - `transcript` feeds straight into the chat input box.
 *   - `speak` reads the agent's answer aloud (toggleable via `ttsEnabled`).
 *
 * Both surfaces degrade gracefully when the browser lacks support, so the
 * chat page still works on headless / test environments.
 */
export function useSpeech(options: UseSpeechOptions = {}) {
  const {
    lang = "zh-CN",
    ttsLang = "zh-CN",
    continuous = false,
    interimResults = true,
  } = options;

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionSupported =
    typeof window !== "undefined" &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  const ttsSupported =
    typeof window !== "undefined" && "speechSynthesis" in window;

  const [speaking, setSpeaking] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  // ---- Speech recognition setup ----
  useEffect(() => {
    if (!recognitionSupported) return;
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = continuous;
    rec.interimResults = interimResults;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      setError(null);
      setListening(true);
    };
    rec.onresult = (e) => {
      let finalText = "";
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) finalText += result[0].transcript;
        else interimText += result[0].transcript;
      }
      if (finalText) {
        setTranscript((prev) => (prev ? prev + finalText : finalText));
      }
      setInterim(interimText);
    };
    rec.onerror = (e) => {
      setError(e.error || "speech-error");
      setListening(false);
    };
    rec.onend = () => {
      setListening(false);
      setInterim("");
    };

    recognitionRef.current = rec;
    return () => {
      try {
        rec.abort();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    };
  }, [lang, continuous, interimResults, recognitionSupported]);

  const startListening = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    setTranscript("");
    setInterim("");
    setError(null);
    try {
      rec.start();
    } catch {
      // start() throws if already started; ignore.
    }
  }, []);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
    setListening(false);
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript("");
    setInterim("");
    setError(null);
  }, []);

  // ---- Text-to-speech ----
  const speak = useCallback(
    (text: string) => {
      if (!ttsSupported || !text) return;
      if (!ttsEnabled) return;
      // Strip markdown-ish markers for cleaner narration.
      const clean = text.replace(/[#*_>`]/g, "").replace(/\s+\n/g, "\n").trim();
      if (!clean) return;
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(clean);
      utter.lang = ttsLang;
      utter.rate = 1;
      utter.pitch = 1;
      utter.onstart = () => setSpeaking(true);
      utter.onend = () => setSpeaking(false);
      utter.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(utter);
    },
    [ttsSupported, ttsEnabled, ttsLang],
  );

  const cancelSpeak = useCallback(() => {
    if (!ttsSupported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [ttsSupported]);

  // Stop narration when the hook unmounts.
  useEffect(() => {
    return () => {
      if (ttsSupported) window.speechSynthesis.cancel();
    };
  }, [ttsSupported]);

  return {
    // recognition
    recognitionSupported,
    listening,
    transcript,
    interim,
    error,
    startListening,
    stopListening,
    resetTranscript,
    // synthesis
    ttsSupported,
    speaking,
    ttsEnabled,
    setTtsEnabled,
    speak,
    cancelSpeak,
  };
}

export type UseSpeechReturn = ReturnType<typeof useSpeech>;
