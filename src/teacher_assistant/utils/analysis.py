
import io
import matplotlib.pyplot as plt
#from matplotlib.patches import Circle
from matplotlib.offsetbox import TextArea, HPacker, AnnotationBbox, VPacker
import matplotlib.lines as mlines

def create_horizontal_stacked_bar(values, colors=None, labels=None):
   
    if colors is None: colors = plt.cm.tab20.colors[:len(values)]

    fig, ax = plt.subplots(figsize=(4, 0.6), dpi=320) 
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    left = 0
    for i, value in enumerate(values):
        ax.barh(0, value, left=left, color=colors[i], height=0.5)
        
        # Add label inside the bar segment
        if labels:
            center = left + value / 2
            ax.text(
                center,
                0,
                labels[i],
                ha='center',
                va='center',
                fontsize=8,
                color='white' if value > 1 else 'black',
                clip_on=True
            )
        
        left += value

    ax.set_xlim(0, sum(values))
    ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.margins(0)  # remove extra margin around plot
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Save with zero padding and tight bbox
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_


def create_vertical_single_stacked_bar(values, colors=None, labels=None):

    if colors is None:
        colors = plt.cm.tab20.colors[:len(values)]

    fig, ax = plt.subplots(figsize=(2, 4), dpi=320)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    bottom = 0
    for i, value in enumerate(values):
        ax.bar(0, value, bottom=bottom, color=colors[i], width=0.5, label=labels[i] if labels else None)
        bottom += value

    ax.set_xlim(-0.5, 1)  # adjust for space
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Add rotated text very close to the bar
    if labels:
        for i, label in enumerate(labels):
            ax.text(
                0.3,  # Closer to bar
                sum(values[:i]) + values[i] / 2,
                label,
                va='center',
                ha='left',
                rotation=90,
                fontsize=8
            )

    fig.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_

def create_donut_image(x1, total=20, dpi=320):
    # Create transparent figure and axis
    fig, ax = plt.subplots(figsize=(3, 3), dpi=dpi)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    # Fill the entire figure area with the axes (remove margins)
    ax.set_position([0, 0, 1, 1])  # [left, bottom, width, height]

    # Donut chart
    ax.pie(
        [x1, total - x1],
        colors=['#33ccff', '#444444'],
        startangle=90,
        wedgeprops={'width': 0.3}
    )

    # Center label
    big_text = TextArea(f"{x1}", textprops=dict(fontsize=28, fontweight='bold', color='#888888'))
    small_text = TextArea(f"/{total}", textprops=dict(fontsize=16, color='#888888'))
    lowered_small_text = VPacker(children=[TextArea(""), small_text], align="center", pad=0, sep=6)
    combined = HPacker(children=[big_text, lowered_small_text], align="center", pad=0, sep=2)
    ab = AnnotationBbox(combined, (0, 0), frameon=False)
    ax.add_artist(ab)

    # Remove axis
    ax.axis('equal')
    ax.axis('off')

    # Save image
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True, pad_inches=0)
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_

def create_line_chart_image(x_values, y_values):
    
    if not x_values: x_values = list(range(1, 1 + len(y_values)))

    # Create figure with dark background
    fig, ax = plt.subplots(figsize=(4, 3), dpi=320)
    fig.patch.set_facecolor('none') # Transparent fig background
    ax.set_facecolor('#1e1e1e')
   
    import matplotlib.ticker as mticker

    yticks = [round(t * 0.2, 1) for t in range(10)]
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_locator(mticker.FixedLocator(yticks))
    ax.yaxis.set_major_formatter(mticker.FixedFormatter([f'{t:.1f}' for t in yticks]))

    # Plot line chart with bright color
    ax.plot(x_values, y_values, marker='o', color='#00bfff',
            linewidth=2, markerfacecolor='orange', markeredgecolor='orange')

    # Customize border (spines)
    for spine in ax.spines.values(): spine.set_color('#888888')            

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(True)
    ax.spines['bottom'].set_visible(True)

    # Customize ticks and labels
    ax.tick_params(axis='x', colors='#888888', labelsize=10)
    ax.tick_params(axis='y', colors='#888888', labelsize=10)
    # Grid: optional but use light lines if you want them
    ax.grid(True,'major', color='#888888', linestyle='--', linewidth=0.5)

    # Save to transparent image
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True) 
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_


def create_normal_bar_chart(values, labels=None, colors=None):


    if colors is None:
        colors = plt.cm.tab10.colors[:len(values)]

    fig, ax = plt.subplots(figsize=(2, 3), dpi=320)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    x = list(range(len(values)))
    bars = ax.bar(x, values, color=colors[:len(values)], width=0.95)

    # Hide x-axis tick labels but keep ticks if needed
    ax.set_xticks(x)
    ax.set_xticklabels([])  # This hides the text labels

    # Hide y-axis ticks and all spines except bottom
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(True)

    # Add rotated text inside each bar
    for i, bar in enumerate(bars):
        height = bar.get_height()
        label_text = labels[i] if labels else str(i)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height / 2,
            label_text,
            ha='center',
            va='center',
            rotation=90,
            fontsize=8,
            rotation_mode='anchor',
            color='white' if height > 1 else 'black',
            clip_on=True
        )

    ax.margins(0)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_


def create_pie_chart(values, labels=None, colors=None,ncol=None):
    if colors is None:  colors = plt.cm.tab20.colors[:len(values)]

    fig, ax = plt.subplots(figsize=(3, 2.5), dpi=320)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    total = sum(values)
    if total == 0:
        return bytes()

    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values,
        colors=colors[:len(values)],
        startangle=90,
        autopct=lambda pct: f'{pct:.1f}%' if total != 0 else '',
        textprops=dict(color='black', fontsize=10),
        #wedgeprops=dict(edgecolor='white')
    )

    ax.axis('equal')
    ax.axis('off')

    # If labels are provided, create custom legend with small squares (cubes)
    if labels:
        # Create small square markers for the legend
        legend_handles = [mlines.Line2D([0], [0], marker='s',  label=label,#color='w',
                          markersize=10, markerfacecolor=color, linestyle='') for label, color in zip(labels, colors)]
        
        n = ncol if type(ncol) is not type(None) else len(labels)
        # Create the legend
        legend = ax.legend(
            handles=legend_handles,
            labels=labels,
            loc='lower center',
            bbox_to_anchor=(0.5, -0.23),  # Move the legend outside the figure to the right
            fontsize=10,
            frameon=False,
            handletextpad=0.85,  # Adjust this value to control the distance between the cube and the text
            handlelength=0,      # Remove the line (tail) connecting the marker and the text
            labelspacing=0.3,    # Adjust the vertical spacing (default is 1.0)
            ncol=n               # Set the number of columns (horizontal layout)
        )
        for text in legend.get_texts(): text.set_color('#666666')

    # Save image without any padding or margins
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    buf.seek(0)
    plt.close(fig)

    bytes_ = buf.read()
    buf.close()
    return bytes_

from matplotlib.legend_handler import HandlerPatch
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgba
import numpy as np

class SquareHandler(HandlerPatch):
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # Get facecolor and handle weird formats (like 2D arrays or single floats)
        facecolor = orig_handle.get_facecolor()

        if isinstance(facecolor, np.ndarray):
            if facecolor.shape == (1, 4):  # A single RGBA row
                rgba = tuple(facecolor[0])
            elif facecolor.shape == (4,):  # Already in proper shape
                rgba = tuple(facecolor)
            else:
                rgba = (0.5, 0.5, 0.5, 1)  # Fallback gray
        elif isinstance(facecolor, (list, tuple)) and len(facecolor) == 4:
            rgba = tuple(facecolor)
        else:
            try:
                rgba = to_rgba(facecolor)
            except:
                rgba = (0.5, 0.5, 0.5, 1)  # Fallback gray

        # Draw square
        size = min(width, height)
        square = Rectangle(
            [xdescent, ydescent],
            size,
            size,
            facecolor=rgba,
            edgecolor=orig_handle.get_edgecolor(),
            transform=trans
        )
        return [square]


