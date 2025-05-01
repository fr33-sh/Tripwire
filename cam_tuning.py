from picamera2 import Picamera2
import PIL
from tripwire.ssim import ssim
import numpy as np

from pathlib import Path
import sys
import os
import yaml
import time


if __name__ == "__main__":

    # Read the config.
    with open("./cam_tuning.yaml") as f:
        tuning_config = yaml.safe_load(f)

    # Set up the paths.
    repo_dir = Path(__file__).resolve().parent
    instance_dir = repo_dir / "instance"
    if not Path.is_dir(instance_dir):
        print(
            "Cannot find the instance directory in the parent directory. "
            "Please don't move this script out of its original location "
            "in the git repo."
        )
        # Don't create the instance dir for the user. If it doesn't
        # exist then there may be more problems.
        sys.exit(1)
    tuning_captures_dir = instance_dir / "cam_tuning_captures"
    tuning_captures_dir.mkdir(exist_ok=True)

    # Check for any existing PNGs in the tuning capture dir.
    if len(os.listdir(tuning_captures_dir)) != 0:
        _input = input(
            "There are some existing files in the tuning capture directory "
            f"at {tuning_captures_dir}.\n"
            "If these are images from a previous tuning session, they may "
            "severely interfere with the current tuning.\n"
            "Are you sure you want to continue? Please type \"n\" to "
            "abort, or \"Y\" if you are really sure you want to continue.\n"
        )
        if _input == "n":
            sys.exit(0)
        elif _input == "Y":
            pass
        else:
            print("Invalid input. Note that it's case-sensitive!")
            sys.exit(0)


    # Config the camera.
    picam = Picamera2()
    cam_config = picam.create_still_configuration(
        main={
            "size": (
                tuning_config["img_width"],
                tuning_config["img_height"]
            )
        }
    )


    # Capture images.
    time_before_cap = time.time()
    picam.start_and_capture_files(
        str(tuning_captures_dir / "{:d}.png"),
        capture_mode=cam_config,
        initial_delay=tuning_config["init_delay"],
        delay=tuning_config["interval"],
        num_files=tuning_config["num_imgs"],
        show_preview=False
    )
    time_after_cap = time.time()
    time_cap = round(time_after_cap - time_before_cap, 1)
    print(f"Spent {time_cap} seconds to capture all the images.")


    # Load the captured images and get the SSIMs.
    img_paths = list(tuning_captures_dir.glob("*.png"))
    if len(img_paths) < 2:
        print(
            "Fewer than two images exist in the tuning capture "
            f"directory at {tuning_captures_dir}.\n"
            "No comparison can be made for tuning. Abording.\n"
            "(Usually you need a lot more than two images for tuning)."
        )
    # Sort the images by their modification times.
    sorted_img_paths = sorted(
        img_paths,
        key=lambda img_path: img_path.stat().st_mtime
    )
    # Sanity check on the sorting of image files.
    assert sorted_img_paths == sorted(img_paths), \
        "Image paths sorted by time are different from them " \
        "being sorted alphabetically. This is abnormal. Aborted."
    time_before_ssim = time.time()
    init_img = None
    min_ssim_vs_init = None
    min_ssim_vs_next = None
    for i, img_path in enumerate(sorted_img_paths):
        img = np.array(PIL.Image.open(img_path))
        if i == 0:
            init_img = img

        ssim_vs_init = ssim(init_img, img)

        if not min_ssim_vs_init or ssim_vs_init < min_ssim_vs_init:
            min_ssim_vs_init = ssim_vs_init

        if i + 1 == len(sorted_img_paths):
            break

        next_img_path = sorted_img_paths[i + 1]
        next_img = np.array(PIL.Image.open(next_img_path))

        ssim_vs_next = ssim(img, next_img)

        if not min_ssim_vs_next or ssim_vs_next < min_ssim_vs_next:
            min_ssim_vs_next = ssim_vs_next

        print(
            f"Image #{i}: SSIM vs the init image: {ssim_vs_init}, "
            f"SSIM vs the next image: {ssim_vs_next}."
        )
    print(f"The minimal SSIM against the initial image is: {min_ssim_vs_init}.")
    print(f"The minimal SSIM between every pair of images is: {min_ssim_vs_next}.")
    time_after_ssim = time.time()
    time_ssim = round(time_after_ssim - time_before_ssim, 1)
    print(f"Spent {time_ssim} seconds to compute the two minimal SSIMs.")

