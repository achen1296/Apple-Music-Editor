"use strict";

const trackQueue = ["test.mp3", "test2.mp3"];
let trackIndex = 0;

const player = document.getElementById("player") as HTMLDivElement;

const currentAudio = document.getElementById("currentAudio") as HTMLAudioElement;

const playTimeSlider = document.getElementById("playTimeSlider") as HTMLInputElement;
const playTimeText = document.getElementById("playTimeText") as HTMLDivElement;

const skipPreviousButton = document.getElementById("skipPreviousButton") as HTMLButtonElement;
const playPauseButton = document.getElementById("playPauseButton") as HTMLButtonElement;
const skipNextButton = document.getElementById("skipNextButton") as HTMLButtonElement;

const volumeSlider = document.getElementById("volumeSlider") as HTMLInputElement;
const volumeText = document.getElementById("volumeText") as HTMLDivElement;

const playRateSlider = document.getElementById("playRateSlider") as HTMLInputElement;
const playRateText = document.getElementById("playRateText") as HTMLDivElement;

function switchTrack(track: string) {
    // todo: right now, the path of the file, but should be changed to Apple Music track ID
    currentAudio.src = `app://trackfile/${track}`;
    currentAudio.playbackRate = Number(playRateSlider.value); // this isn't remembered automatically (unlike volume)
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
    volumeText.innerText = `${volumeSlider.value}%`;
});

playRateSlider.addEventListener("input", ev => {
    currentAudio.playbackRate = Number(playRateSlider.value);
    playRateText.innerText = `${playRateSlider.value}x speed`;
});

switchTrack(trackQueue[0]);