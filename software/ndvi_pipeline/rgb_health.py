import cv2
import numpy as np
import matplotlib.pyplot as plt

def rgb_cell_score(hsv_cell):
    h, s, v = hsv_cell[:,:,0], hsv_cell[:,:,1], hsv_cell[:,:,2]

    not_shadow = v > 30
    not_sky = ~((h > 90) & (h < 130) & (s > 50))
    valid = not_shadow & not_sky

    green_mask = (h >= 35) & (h <= 85) & (s > 80) & valid
    brown_mask = (h >= 10) & (h < 35) & valid

    green_count = np.sum(green_mask)
    brown_count = np.sum(brown_mask)

    if green_count + brown_count == 0:
        return 0.0

    return green_count / (green_count + brown_count)

def rgb_health_grid(image_path, grid_size=4, label='test'):
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]
    cell_h, cell_w = h // grid_size, w // grid_size

    scores = np.zeros((grid_size, grid_size))
    for i in range(grid_size):
        for j in range(grid_size):
            cell = hsv[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            scores[i, j] = rgb_cell_score(cell)

    masked_scores = np.ma.masked_equal(scores, 0)
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='black')

    plt.figure(figsize=(6, 6))
    plt.imshow(masked_scores, cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(label='Health Score (0-1)')
    plt.title(f'RGB Grid Health Map - {label} ({grid_size}x{grid_size})')
    for i in range(grid_size):
        for j in range(grid_size):
            text_color = 'black' if scores[i,j] == 0 else 'black'
            plt.text(j, i, f'{scores[i,j]:.2f}', ha='center', va='center',
                     color=text_color, fontsize=10)
    plt.savefig(f'data/drone_imagery/rgb_grid_{label}.png', dpi=150)
    plt.close()
    print(f"Saved to data/drone_imagery/rgb_grid_{label}.png")
    print(scores)
    return scores

if __name__ == '__main__':
    rgb_health_grid('data/drone_imagery/test/healthy_image.jpg', grid_size=6, label='healthy')

