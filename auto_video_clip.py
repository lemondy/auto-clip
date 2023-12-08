# encoding: utf-8


import os
import random
import sys

import argparse
from skimage.filters import gaussian
import moviepy.editor as mp
from moviepy.editor import CompositeVideoClip
from moviepy.editor import vfx

def blur(image):
    """
    return a blurred (radius=2 pixels) version of image
    """
    return gaussian(image.astype(float), sigma=30)

def reset_size_blur(video_path: str) -> mp.VideoFileClip:
    """ reset the video size, default 1:1, and will make the background blur
    """
    video = mp.VideoFileClip(video_path, audio=False, has_mask="True").resize(4)
    # 将视频放大并加蒙版遮罩
    video_blur = video.image_transform(blur)
    # 将小的视频叠在大视频的居中位置
    concat_video = CompositeVideoClip([video_blur, video.set_pos("center")])
    # 对叠好的视频进行剪切
    final_cut = concat_video.crop(x1=0, x2=video.w, y1=(video_blur.h - video.h) / 2, y2=video.h + (video_blur.h - video.h) / 2)
    final_cut = final_cut.resize(height=video.h)
    return final_cut

def load_videos(video_root_path:str, 
                video_cut_duration:float=0.2, 
                is_cut_randomly:bool=False,
                video_speed=1.0
                )-> list:
    """ load video from path and cut the begin and end video_cut_duration
    """

    video_list = []
    if is_cut_randomly:
        video_cut_duration = random.uniform(0.1, 1.0)

    for video_file in sorted(os.listdir(video_root_path)):
        print(video_file)
        if "mp4" not in video_file:
            continue
        
        video = reset_size_blur("{}/{}".format(video_root_path, video_file))
        video_duration = video.duration
        # 去掉视频开头和结尾 n second
        trimmed_video = video.subclip(video_cut_duration, video_duration - video_cut_duration)
        # 改变视频播放速度
        speed_video = trimmed_video.fx(vfx.speedx, video_speed)
        print("video:{}, source duraion:{}, trimmed duration:{}".format(video_file, video_duration, trimmed_video.duration))
        video_list.append(speed_video)

    return video_list


def concat_video(video_list:list, padding=0.5):
    """
    concat video 添加叠化转场效果
    parameters:
        padding: float, seconds
        video_list: list
    """
    
    if not video_list:
        print("concat_video error: video_list is empty")
        return None
    
    video_fx_list = [video_list[0]]
    # set padding to initial video
    idx = video_list[0].duration - padding

    for video in video_list[1:]:
        video_fx_list.append(video.set_start(idx).crossfadein(padding))
        idx += video.duration - padding

    final_video = CompositeVideoClip(video_fx_list)
    return final_video
    # final_video.write_videofile('concat_video.mp4', fps=24)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--vrp", "--video_root_path", type=str, default="./video_demo/", help="video root path")
    parser.add_argument("--vcr", "--video_cut_randomly", type=bool, default=False, help="video cut randomly")
    parser.add_argument("--wmp", "--watermark_path", type=str, default="./video_demo/watermark.mov", help="watermark video path")
    parser.add_argument("--out", "--output_path", type=str, default="./output.mp4", help="output video path")
    parser.add_argument("--vsp", "--video_speed", type=float, default=1.0, help="video speed",)

    args = parser.parse_args()

    # load nickname video
    nickname_video = mp.VideoFileClip(args.wmp)

    video_list = load_videos(args.vrp, is_cut_randomly=args.vcr, video_speed=args.vsp)

    final_videos = concat_video(video_list)
    final_videos.write_videofile(args.out, 
                                 fps=30, 
                                 codec="h264_nvenc", 
                                 threads=15, 
                                 bitrate="1000k",
                                 ffmpeg_params=[
                                     "-tile-columns", "6",
                                     "-frame-parallel", "0",
                                     "-auto-alt-ref", "1",
                                     "-lag-in-frames", "25",
                                     "-g", "128",
                                     "-pix_fmt", "yuv420p",
                                     "-row-mt", "1"
                                 ])
