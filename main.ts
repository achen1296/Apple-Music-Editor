import { net } from 'electron';
import { app, BrowserWindow, protocol } from 'electron/main';
import { pathToFileURL } from 'node:url';

const createWindow = () => {
    const win = new BrowserWindow({
        width: 800,
        height: 600
    });

    win.loadFile('index.html');
};

protocol.registerSchemesAsPrivileged([
    { scheme: "app", privileges: { stream: true, bypassCSP: true } }
]);

app.whenReady().then(() => {
    createWindow();

    protocol.handle("app", (req) => {
        const { host, pathname } = new URL(req.url);

        if (host === "track") {
            // todo for testing
            return net.fetch(pathToFileURL("test.mp3").toString());
        }

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