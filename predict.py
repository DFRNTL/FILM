import os
from pathlib import Path
import numpy as np
import tempfile
import tensorflow as tf
import mediapy
from PIL import Image
from cog import BasePredictor, Input
from typing import Any

from eval import interpolator, util

import tensorflow as tf

_UINT8_MAX_F = float(np.iinfo(np.uint8).max)


class Predictor(BasePredictor):
    def predict(
        self, 
        frame1: str = Input(description="frame1"), 
        frame2: str = Input(description="frame2"), 
        times_to_interpolate: str = Input(description="times_to_interpolate", default=1)
        ) -> Any:

        print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
        self.interpolator = interpolator.Interpolator("pretrained_models/film_net/Style/saved_model", None)

        # Batched time.
        self.batch_dt = np.full(shape=(1,), fill_value=0.5, dtype=np.float32)

        INPUT_EXT = ['.png', '.jpg', '.jpeg']
        assert os.path.splitext(str(frame1))[-1] in INPUT_EXT and os.path.splitext(str(frame2))[-1] in INPUT_EXT, \
            "Please provide png, jpg or jpeg images."

        # make sure 2 images are the same size
        img1 = Image.open(str(frame1))
        img2 = Image.open(str(frame2))
        if not img1.size == img2.size:
            img1 = img1.crop((0, 0, min(img1.size[0], img2.size[0]), min(img1.size[1], img2.size[1])))
            img2 = img2.crop((0, 0, min(img1.size[0], img2.size[0]), min(img1.size[1], img2.size[1])))
            frame1 = 'new_frame1.png'
            frame2 = 'new_frame2.png'
            img1.save(frame1)
            img2.save(frame2)

        if times_to_interpolate == 1:
            # First batched image.
            image_1 = util.read_image(str(frame1))
            image_batch_1 = np.expand_dims(image_1, axis=0)
    
            # Second batched image.
            image_2 = util.read_image(str(frame2))
            image_batch_2 = np.expand_dims(image_2, axis=0)
    
            # Invoke the model once.
            
            mid_frame = self.interpolator.interpolate(image_batch_1, image_batch_2, self.batch_dt)[0]
            out_path = Path(tempfile.mkdtemp()) / "out.png"
            util.write_image(str(out_path), mid_frame)
            return out_path


        input_frames = [str(frame1), str(frame2)]

        frames = list(
            util.interpolate_recursively_from_files(
                input_frames, times_to_interpolate, self.interpolator))
        print('Interpolated frames generated, saving now as output video.')

        ffmpeg_path = util.get_ffmpeg_path()
        mediapy.set_ffmpeg(ffmpeg_path)
        out_path = Path(tempfile.mkdtemp()) / "out.mp4"
        mediapy.write_video(str(out_path), frames, fps=30)
        return out_path
