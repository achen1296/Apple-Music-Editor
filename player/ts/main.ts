import { net } from 'electron';
import { app, BrowserWindow, protocol } from 'electron/main';
import { ChildProcess, spawn } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import * as zmq from "zeromq";

console.log(__dirname);

const BACKEND_PORT = 0xA91E; // hexspeak approximation of "Apple" which is also a valid port

const createWindow = () => {
    const win = new BrowserWindow({
        show: false,
    });

    win.maximize();
    win.show();

    win.loadFile("index.html");
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

let childProcess: ChildProcess | null = null;

function spawnBackend() {
    if (childProcess) {
        return
    }
    childProcess = spawn(
        "python",
        [
            path.join(__dirname, "electron_backend.py"),
            `${BACKEND_PORT}`,
        ]
    );
    if (!childProcess) {
        throw Error("couldn't spawn backend child process");
    }
}

function killBackend() {
    if (childProcess) {
        childProcess.kill();
        childProcess = null;
    }
}

const FILE_PATH_HOSTS = [
    "trackfile",
    "artwork"
];

async function backendRequest(url: string) {
    const sock = new zmq.Request();
    sock.connect(`tcp://localhost:${BACKEND_PORT}`);
    await sock.send(url);
    const [result] = await sock.receive();
    return result.toString();
}

app.whenReady().then(() => {
    spawnBackend();

    createWindow();

    protocol.handle("app", async (req) => {
        // use host to determine how to interpret the result, but the rest of the URL parsing is done on the Python side
        const { host } = new URL(req.url);

        const response = await backendRequest(req.url);

        if (response.startsWith("error ")) {
            return new Response(response.slice("error ".length), {
                status: 400,
                headers: { "content-type": "text/html" }
            });
        }

        if (FILE_PATH_HOSTS.includes(host)) {
            return net.fetch(pathToFileURL(response.toString()).toString());
        } else {
            return new Response(response, {
                status: 200,
                headers: { "content-type": "text" }
        });
        }
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