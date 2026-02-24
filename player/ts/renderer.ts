"use strict";

declare function backendRequest(url: string): Promise<string>;

// player

const playerDiv = document.getElementById("player") as HTMLDivElement;

const currentTrackNameText = document.getElementById("currentTrackNameText") as HTMLSpanElement;
const currentTrackArtistText = document.getElementById("currentTrackArtistText") as HTMLSpanElement;
const currentTrackAlbumText = document.getElementById("currentTrackAlbumText") as HTMLSpanElement;

const currentAudio = document.getElementById("currentAudio") as HTMLAudioElement;

const playTimeSlider = document.getElementById("playTimeSlider") as HTMLInputElement;
const playTimeText = document.getElementById("playTimeText") as HTMLSpanElement;

const skipPreviousButton = document.getElementById("skipPreviousButton") as HTMLButtonElement;
const playPauseButton = document.getElementById("playPauseButton") as HTMLButtonElement;
const skipNextButton = document.getElementById("skipNextButton") as HTMLButtonElement;

const volumeSlider = document.getElementById("volumeSlider") as HTMLInputElement;
const volumeText = document.getElementById("volumeText") as HTMLSpanElement;

const playRateSlider = document.getElementById("playRateSlider") as HTMLInputElement;
const playRateText = document.getElementById("playRateText") as HTMLSpanElement;

async function switchTrack(trackID: string) {
    if (!trackID) {
        return; // e.g. undefined for empty track queue, silently ignore
    }
    currentAudio.src = `app://trackfile/${trackID}`;

    currentAudio.playbackRate = Number(playRateSlider.value); // this isn't remembered automatically (unlike volume)

    const trackMeta = JSON.parse(await backendRequest(`app://trackmeta/${trackID}`));
    const { name, album, artist } = trackMeta;

    currentTrackNameText.innerText = name;
    currentTrackArtistText.innerText = artist || "(no artist)";
    currentTrackAlbumText.innerText = album || "(no album)";
}

let trackQueue: string[] = [];
let trackIndex = 0;

function switchTrackQueue(newTrackQueue: string[]) {
    trackQueue = newTrackQueue.filter(i => i); // remove empty strings from splitting e.g. "".split(" ") -> [""]
    trackIndex = 0;
    switchTrack(trackQueue[0]);
}

function previousTrack() {
    trackIndex--;
    trackIndex %= trackQueue.length;
    switchTrack(trackQueue[trackIndex]);
}

function nextTrack() {
    trackIndex++;
    trackIndex %= trackQueue.length;
    switchTrack(trackQueue[trackIndex]);
}

const SECONDS_FORMAT = Intl.NumberFormat(undefined, {
    minimumIntegerDigits: 2
});

function setPlayTimeText(totalSeconds: number) {
    let seconds = totalSeconds % 60;
    const minutes = (totalSeconds - seconds) / 60;
    seconds = Math.floor(seconds);
    playTimeText.innerText = `${minutes}:${SECONDS_FORMAT.format(seconds)}`;
}

currentAudio.addEventListener("timeupdate", ev => {
    const newLocal = currentAudio.currentTime;
    setPlayTimeText(newLocal);
    playTimeSlider.value = `${currentAudio.currentTime}`;
});

let inputtingOnPlayTimeSlider = false;
let audioWasPausedBeforeSeek = false;

playTimeSlider.addEventListener("input", ev => {
    if (!inputtingOnPlayTimeSlider) {
        // otherwise gets input many times quickly almost guaranteeing that audioWasPausedBeforeSeek will be set to true
        audioWasPausedBeforeSeek = currentAudio.paused;
        inputtingOnPlayTimeSlider = true;
    }
    currentAudio.pause(); // halt playback while seeking, and so the audio playback doesn't compete to set the play time text
    setPlayTimeText(Number(playTimeSlider.value));
});

playTimeSlider.addEventListener("change", ev => {
    if (!audioWasPausedBeforeSeek) {
        currentAudio.play(); // resume if was playing before
    }
    inputtingOnPlayTimeSlider = false;
    currentAudio.currentTime = Number(playTimeSlider.value);
});

currentAudio.addEventListener("durationchange", ev => {
    playTimeSlider.max = `${currentAudio.duration}`;
});

skipPreviousButton.addEventListener("click", ev => {
    previousTrack();
});

skipNextButton.addEventListener("click", ev => {
    nextTrack();
});

currentAudio.addEventListener("ended", ev => {
    nextTrack();
});

playPauseButton.addEventListener("click", ev => {
    if (currentAudio.paused) {
        currentAudio.play();
    } else {
        currentAudio.pause();
    }
});

volumeSlider.addEventListener("input", ev => {
    currentAudio.volume = Number(volumeSlider.value) / 100;
    volumeText.innerText = `${volumeSlider.value}% volume`;
});

playRateSlider.addEventListener("input", ev => {
    const playRate = Number(playRateSlider.value);
    currentAudio.playbackRate = playRate;
    // number of decimal digits matches slider step 0.1
    playRateText.innerText = `${playRate.toFixed(1)}x speed`;
});

// album and playlist lists

const albumsDiv = document.getElementById("albums") as HTMLDivElement;
const albumList = document.getElementById("albumList") as HTMLUListElement;

const playlistsDiv = document.getElementById("playlists") as HTMLDivElement;
const playlistList = document.getElementById("playlistList") as HTMLUListElement;


async function loadAlbumList() {
    const albumIDs = await backendRequest("app://albumlist");
    if (albumList.firstElementChild) {
        // remove "Loading..."
        albumList.removeChild(albumList.firstElementChild);
    }
    for (const albumID of albumIDs.split(" ")) {
        const a = albumList
            .appendChild(document.createElement("li"))
            .appendChild(document.createElement("a"));
        const albumMeta = JSON.parse(await backendRequest(`app://albummeta/${albumID}`));
        const { name, artist } = albumMeta;
        a.innerText = `${name}${artist ? ` by ${artist}` : ""}`;
        a.addEventListener("click", async ev => {
            switchTrackQueue((await backendRequest(`app://albumitems/${albumID}`)).split(" "));
        });
    }
}

loadAlbumList();

async function loadPlaylistList() {
    const playlistIDs = await backendRequest("app://playlistlist");
    if (playlistList.firstElementChild) {
        // remove "Loading..."
        playlistList.removeChild(playlistList.firstElementChild);
    }
    for (const playlistID of playlistIDs.split(" ")) {
        const a = playlistList
            .appendChild(document.createElement("li"))
            .appendChild(document.createElement("a"));
        const playlistMeta = JSON.parse(await backendRequest(`app://playlistmeta/${playlistID}`));
        a.innerText = playlistMeta["name"];
        a.addEventListener("click", async ev => {
            switchTrackQueue((await backendRequest(`app://playlistitems/${playlistID}`)).split(" "));
        });
    }
}

loadPlaylistList();