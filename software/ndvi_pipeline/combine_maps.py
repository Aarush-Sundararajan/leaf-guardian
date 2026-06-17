import numpy as np
import matplotlib.pyplot as plt

def combine_health_maps(rgb_scores, ndvi_scores, label='combined'):
    if rgb_scores.shape != ndvi_scores.shape:
        raise ValueError("Grids must match in size to combine")

    grid_size = rgb_scores.shape[0]

    # Combined score: average of the two sensors
    combined = (rgb_scores + ndvi_scores) / 2

    # Discrepancy: where the two sensors disagree
    discrepancy = np.abs(rgb_scores - ndvi_scores)

    masked = np.ma.masked_equal(combined, 0)
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='black')

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    axes[0].imshow(masked, cmap=cmap, vmin=0, vmax=1)
    axes[0].set_title('Combined Health Map')
    for i in range(grid_size):
        for j in range(grid_size):
            axes[0].text(j, i, f'{combined[i,j]:.2f}', ha='center', va='center', fontsize=8)

    im = axes[1].imshow(discrepancy, cmap='Reds', vmin=0, vmax=1)
    axes[1].set_title('RGB vs NDVI Discrepancy')
    plt.colorbar(im, ax=axes[1])

    plt.tight_layout()
    plt.savefig(f'data/sentinel_data/combined_maps/combined_map_{label}.png', dpi=150)
    plt.close()
    print(f"Saved to data/sentinel_data/combined_maps/combined_map_{label}.png")
    return combined, discrepancy