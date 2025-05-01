from skimage.metrics import structural_similarity


def ssim(img_arr1, img_arr2):
    return structural_similarity(
        img_arr1,
        img_arr2,
        # This follows the example on skimage's docs.
        data_range=img_arr2.max() - img_arr2.min(),
        channel_axis=2
    )
