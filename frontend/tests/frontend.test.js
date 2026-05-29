/**
 * frontend/tests/frontend.test.js
 *
 * Testy jednostkowe frontendu.
 * Uruchamianie: cd frontend/tests && npm install && npm test
 *
 * Testuje:
 *  - Obecność kluczowych elementów DOM
 *  - Zachowanie logiki UI (enable/disable przycisku, preview, reset)
 *  - Obsługę odpowiedzi z API
 */

const fs   = require("fs");
const path = require("path");

// ── Wczytaj HTML przed każdym testem ────────────────────────────────────────
const HTML_PATH = path.join(__dirname, "../index.html");
const RAW_HTML  = fs.readFileSync(HTML_PATH, "utf8");

beforeEach(() => {
    document.documentElement.innerHTML = RAW_HTML;
    // Wyczyść globalne stany JS załadowane ze skryptu inline
    jest.resetModules();
    jest.restoreAllMocks();
});


// ── 1. Struktura DOM ─────────────────────────────────────────────────────────

describe("Struktura DOM", () => {
    test("strona zawiera formularz z id=upload-form", () => {
        expect(document.getElementById("upload-form")).not.toBeNull();
    });

    test("formularz zawiera input[type=file]", () => {
        const inp = document.querySelector('input[type="file"]');
        expect(inp).not.toBeNull();
    });

    test("input pliku akceptuje obrazy (accept=image/*)", () => {
        const inp = document.getElementById("file-input");
        expect(inp.getAttribute("accept")).toContain("image");
    });

    test("przycisk submit istnieje", () => {
        const btn = document.getElementById("submit-btn");
        expect(btn).not.toBeNull();
    });

    test("przycisk submit jest początkowo wyłączony", () => {
        const btn = document.getElementById("submit-btn");
        expect(btn.disabled).toBe(true);
    });

    test("sekcja wynikowa jest początkowo ukryta", () => {
        const sec = document.getElementById("result-section");
        expect(sec.classList.contains("hidden")).toBe(true);
    });

    test("drop-zone istnieje", () => {
        expect(document.getElementById("drop-zone")).not.toBeNull();
    });

    test("kontener podglądu jest początkowo ukryty", () => {
        const pc = document.getElementById("preview-container");
        expect(pc.classList.contains("hidden")).toBe(true);
    });

    test("przycisk usunięcia zdjęcia istnieje", () => {
        expect(document.getElementById("remove-btn")).not.toBeNull();
    });

    test("element stanu ładowania istnieje", () => {
        expect(document.getElementById("state-loading")).not.toBeNull();
    });

    test("element stanu sukcesu istnieje", () => {
        expect(document.getElementById("state-success")).not.toBeNull();
    });

    test("element stanu błędu istnieje", () => {
        expect(document.getElementById("state-error")).not.toBeNull();
    });
});


// ── 2. Zachowanie UI ─────────────────────────────────────────────────────────

describe("Zachowanie UI", () => {
    test("drag-over dodaje klasę .drag-over do drop-zone", () => {
        const dz = document.getElementById("drop-zone");
        const ev = new Event("dragover");
        ev.preventDefault = jest.fn();
        dz.dispatchEvent(ev);
        expect(dz.classList.contains("drag-over")).toBe(true);
    });

    test("dragleave usuwa klasę .drag-over z drop-zone", () => {
        const dz = document.getElementById("drop-zone");
        dz.classList.add("drag-over");
        dz.dispatchEvent(new Event("dragleave"));
        expect(dz.classList.contains("drag-over")).toBe(false);
    });

    test("kliknięcie remove-btn ukrywa preview i pokazuje drop-zone", () => {
        // Zasymuluj stan z obrazem
        const previewCont = document.getElementById("preview-container");
        const dropZone    = document.getElementById("drop-zone");
        previewCont.classList.remove("hidden");
        dropZone.classList.add("hidden");

        document.getElementById("remove-btn").click();

        expect(dropZone.classList.contains("hidden")).toBe(false);
        expect(previewCont.classList.contains("hidden")).toBe(true);
    });

    test("kliknięcie remove-btn wyłącza przycisk submit", () => {
        document.getElementById("submit-btn").disabled = false;
        document.getElementById("remove-btn").click();
        expect(document.getElementById("submit-btn").disabled).toBe(true);
    });

    test("kliknięcie remove-btn chowa sekcję wynikową", () => {
        const resultSec = document.getElementById("result-section");
        resultSec.classList.remove("hidden");
        document.getElementById("remove-btn").click();
        expect(resultSec.classList.contains("hidden")).toBe(true);
    });
});


// ── 3. Fetch + wyświetlanie wyników ──────────────────────────────────────────

describe("Komunikacja z API i wyniki", () => {
    function armWithFile() {
        const fileInput = document.getElementById("file-input");
        const submitBtn = document.getElementById("submit-btn");
        // jsdom nie pozwala przypisać .files bezpośrednio, ale możemy
        // mockować odczyt przez Object.defineProperty
        const fakeFile = new File(["data"], "skin.jpg", { type: "image/jpeg" });
        Object.defineProperty(fileInput, "files", {
            value: [fakeFile],
            writable: false,
            configurable: true,
        });
        submitBtn.disabled = false;
        return fakeFile;
    }

    test("formularz woła fetch('/api/analyze') przy submit", async () => {
        armWithFile();
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ prediction: "benign", confidence: 0.9, model_used: "m1" }),
        });

        document.getElementById("upload-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await Promise.resolve(); // flush microtasks

        expect(global.fetch).toHaveBeenCalledWith("/api/analyze", expect.any(Object));
    });

    test("po sukcesie 'benign' sekcja wynikowa jest widoczna", async () => {
        armWithFile();
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ prediction: "benign", confidence: 0.88, model_used: "resnet50" }),
        });

        document.getElementById("upload-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        // Poczekaj na async fetch
        await new Promise(r => setTimeout(r, 50));

        const sec = document.getElementById("result-section");
        expect(sec.classList.contains("hidden")).toBe(false);
    });

    test("po błędzie HTTP state-error jest widoczny", async () => {
        armWithFile();
        global.fetch = jest.fn().mockResolvedValue({
            ok: false,
            status: 503,
            json: async () => ({ detail: "AI service unavailable" }),
        });

        document.getElementById("upload-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 50));

        const errState = document.getElementById("state-error");
        expect(errState.classList.contains("hidden")).toBe(false);
    });

    test("po błędzie sieciowym state-error jest widoczny", async () => {
        armWithFile();
        global.fetch = jest.fn().mockRejectedValue(new TypeError("Network error"));

        document.getElementById("upload-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 50));

        const errState = document.getElementById("state-error");
        expect(errState.classList.contains("hidden")).toBe(false);
    });
});
