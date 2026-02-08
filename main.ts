import { net } from 'electron';
import { app, BrowserWindow, protocol } from 'electron/main';
import { ChildProcess, spawn } from 'node:child_process';
import path, { dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import * as zmq from "zeromq";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const BACKEND_PORT = 0xA91E; // hexspeak approximation of "Apple" which is also a valid port

const createWindow = () => {
    const win = new BrowserWindow({
        width: 800,
        height: 600
    });

    win.loadFile('index.html');
};

protocol.registerSchemesAsPrivileged([
    {
        scheme: "app",
        privileges: {
            stream: true,
            bypassCSP: true
        }
    }
]);

let childProcess: ChildProcess;

console.log(__dirname)

function spawnBackend() {
    childProcess = spawn(
        "python",
        [
            path.join(__dirname, "electron_backend.py"),
            `${BACKEND_PORT}`,
        ]
    );
    if (!childProcess) {
        throw Error("couldn't backend spawn child process");
    }
}

function killBackend() {
    if (childProcess) {
        childProcess.kill();
    }
}

app.on('will-quit', killBackend);

app.whenReady().then(() => {
    spawnBackend();

    createWindow();

    protocol.handle("app", async (req) => {
        const { host, pathname } = new URL(req.url);

        if (host === "track") {
            const sock = new zmq.Request();

            sock.connect(`tcp://localhost:${BACKEND_PORT}`)

            await sock.send("4");
            const [result] = await sock.receive();

            return net.fetch(pathToFileURL(result.toString()).toString());
        }
        // else if (host === "album") {}
        // else if (host === "playlist") {}
        // else if (host === "artwork") {}

        return new Response("unknown host", {
            status: 400,
            headers: { 'content-type': 'text/html' }
        });
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});