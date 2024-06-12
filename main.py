import pydub
from moviepy.editor import *
import vosk
import json


def find_silence(video, silence_threshold=-20, mn_silence_duration=750):
    file_name = 'res/audio.wav'
    video.audio.write_audiofile(file_name, logger=None)
    audio = pydub.AudioSegment.from_file(file_name)

    starts = []
    ends = []

    current_start = None

    for i in range(len(audio)):
        if audio[i].dBFS < silence_threshold and current_start is None:
            current_start = i
        elif audio[i].dBFS >= silence_threshold:
            if current_start is not None and i - current_start > mn_silence_duration:
                starts.append(current_start)
                ends.append(i)
            current_start = None

    if current_start is not None:
        starts.append(current_start)
        ends.append(len(audio))

    r = [(start / 1000, end / 1000) for start, end in zip(starts, ends)]

    if r[0][0] == 0:
        r = r[1:]

    return r


def get_non_silences(silences):
    r = []

    last = 0
    for start, end in silences:
        r.append((last, start))
        last = end

    return r


def split_to_clips(video, non_silences):
    clips = []

    for start, end in non_silences:
        dl = .3
        start -= dl if start - dl >= 0 else 0
        end += dl
        clips.append(video.subclip(start, end))

    return clips


def recognize_text(clip):
    file_name = 'res/audio_piece.wav'

    audio = clip.audio
    audio.write_audiofile(file_name, logger=None)

    audio = pydub.AudioSegment.from_file(file_name)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    data = audio.raw_data

    rec.AcceptWaveform(data)
    result = rec.Result()

    return json.loads(result)['text']


def speed_up(video, clip, non_silences, i):
    start = non_silences[i][1]
    end = non_silences[i + 1][0] if i + 1 < len(clips) else None

    video_piece = video.subclip(start, end).without_audio()
    audio_piece = clip.audio

    r = video_piece.fx(vfx.speedx, video_piece.duration / audio_piece.duration)
    r = r.set_audio(audio_piece)

    return r


# объявляем переменные
video = VideoFileClip('res/2024-06-07 17-55-52.mp4')
rec = vosk.KaldiRecognizer(vosk.Model('vosk-model'), 16000)


# получаем кусочки и разбиваем видео
silences = find_silence(video)
non_silences = get_non_silences(silences)
clips = split_to_clips(video, non_silences)


# выводим текст кусков
for i, clip in enumerate(clips):
    text = recognize_text(clip)
    start, end = non_silences[i]

    print(f'{i + 1}. {start}-{end}: {text}')


# удалением лишнее
ns = sorted(list(map(lambda x: int(x) - 1, input('Удалить: ').split())), reverse=True)
[clips.pop(i) for i in ns]
[non_silences.pop(i) for i in ns]


# ускоряем
result = [speed_up(video, clip, non_silences, i) for i, clip in enumerate(clips)]


# собираем
video = concatenate_videoclips(result)


# создаем фон
video = video.resize(1.25)
left_part = video.crop(x1=0, y1=0, x2=1080, y2=1440)
background = ColorClip((1080, 1920), color=(28, 31, 32), duration=video.duration)
final_video = CompositeVideoClip([background, left_part.set_position(("center", "center"))])


final_video.write_videofile('exp.mp4')
