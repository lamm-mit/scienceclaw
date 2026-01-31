#!/usr/bin/env python3
"""
Scientific Data Visualization Tool for ScienceClaw

Creates publication-quality plots using matplotlib and seaborn.
"""

import argparse
import json
import os
import sys
from io import StringIO
from typing import Optional, List, Tuple

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Error: Required packages missing. Install with: pip install matplotlib seaborn pandas numpy")
    print(f"Missing: {e}")
    sys.exit(1)


def load_data(data_path: Optional[str] = None, json_str: Optional[str] = None) -> pd.DataFrame:
    """
    Load data from CSV file or JSON string.

    Args:
        data_path: Path to CSV file
        json_str: JSON string with data

    Returns:
        pandas DataFrame
    """
    if json_str:
        data = json.loads(json_str)
        return pd.DataFrame(data)
    elif data_path:
        if data_path.endswith('.csv'):
            return pd.read_csv(data_path)
        elif data_path.endswith('.tsv'):
            return pd.read_csv(data_path, sep='\t')
        elif data_path.endswith('.json'):
            return pd.read_json(data_path)
        else:
            # Try CSV first
            return pd.read_csv(data_path)
    else:
        raise ValueError("Either --data or --json is required")


def setup_figure(
    figsize: Tuple[float, float] = (10, 6),
    style: str = "whitegrid",
    palette: str = "deep"
) -> Tuple[plt.Figure, plt.Axes]:
    """Set up figure with style."""
    sns.set_style(style)
    sns.set_palette(palette)

    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def apply_common_options(
    ax: plt.Axes,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    logx: bool = False,
    logy: bool = False,
    legend_loc: Optional[str] = None
):
    """Apply common plot options."""
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12)
    if logx:
        ax.set_xscale('log')
    if logy:
        ax.set_yscale('log')
    if legend_loc and ax.get_legend():
        ax.legend(loc=legend_loc)


def save_figure(
    fig: plt.Figure,
    output: str,
    format: str = "png",
    dpi: int = 150
):
    """Save figure to file."""
    # Ensure output has correct extension
    if not output.endswith(f'.{format}'):
        output = f"{output}.{format}"

    fig.tight_layout()
    fig.savefig(output, format=format, dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    print(f"Plot saved to: {output}")
    return output


def plot_line(args) -> str:
    """Create line plot."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    y_cols = [c.strip() for c in args.y.split(',')] if ',' in args.y else [args.y]

    if args.hue and args.hue in df.columns:
        for y_col in y_cols:
            sns.lineplot(
                data=df, x=args.x, y=y_col, hue=args.hue,
                style=args.line_style if hasattr(args, 'line_style') else None,
                markers=args.markers,
                ax=ax
            )
    else:
        for y_col in y_cols:
            label = y_col if len(y_cols) > 1 else None
            sns.lineplot(
                data=df, x=args.x, y=y_col,
                markers=args.markers,
                label=label,
                ax=ax
            )

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or args.y, args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def plot_scatter(args) -> str:
    """Create scatter plot."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    scatter_kwargs = {
        'data': df,
        'x': args.x,
        'y': args.y,
        'alpha': args.alpha,
        'ax': ax
    }

    if args.hue and args.hue in df.columns:
        scatter_kwargs['hue'] = args.hue
    if args.size and args.size in df.columns:
        scatter_kwargs['size'] = args.size

    sns.scatterplot(**scatter_kwargs)

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or args.y, args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def plot_bar(args) -> str:
    """Create bar chart."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    bar_kwargs = {
        'data': df,
        'x': args.y if args.horizontal else args.x,
        'y': args.x if args.horizontal else args.y,
        'ax': ax,
        'orient': 'h' if args.horizontal else 'v'
    }

    if args.hue and args.hue in df.columns:
        bar_kwargs['hue'] = args.hue

    sns.barplot(**bar_kwargs)

    # Add error bars if specified
    if args.error and args.error in df.columns:
        # This would require additional handling for grouped bars
        pass

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or args.y, args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def plot_heatmap(args) -> str:
    """Create heatmap."""
    df = load_data(args.data, args.json)

    # If first column looks like row labels, use it as index
    if df.iloc[:, 0].dtype == 'object':
        df = df.set_index(df.columns[0])

    # Convert to numeric
    df = df.apply(pd.to_numeric, errors='coerce')

    if args.cluster:
        # Use clustermap for hierarchical clustering
        g = sns.clustermap(
            df,
            cmap=args.cmap,
            annot=args.annotate,
            figsize=args.figsize,
            fmt='.2f' if args.annotate else None
        )
        if args.title:
            g.fig.suptitle(args.title, fontsize=14, fontweight='bold', y=1.02)
        g.savefig(args.output, format=args.format, dpi=args.dpi, bbox_inches='tight')
        plt.close(g.fig)
    else:
        fig, ax = setup_figure(args.figsize, args.style, args.palette)
        sns.heatmap(
            df,
            cmap=args.cmap,
            annot=args.annotate,
            fmt='.2f' if args.annotate else None,
            ax=ax
        )
        if args.title:
            ax.set_title(args.title, fontsize=14, fontweight='bold')
        save_figure(fig, args.output, args.format, args.dpi)

    print(f"Plot saved to: {args.output}")
    return args.output


def plot_box(args) -> str:
    """Create box plot."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    box_kwargs = {
        'data': df,
        'y': args.y,
        'ax': ax
    }

    if args.x and args.x in df.columns:
        box_kwargs['x'] = args.x
    if args.hue and args.hue in df.columns:
        box_kwargs['hue'] = args.hue

    sns.boxplot(**box_kwargs)

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or args.y, args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def plot_violin(args) -> str:
    """Create violin plot."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    violin_kwargs = {
        'data': df,
        'y': args.y,
        'ax': ax,
        'split': args.split
    }

    if args.x and args.x in df.columns:
        violin_kwargs['x'] = args.x
    if args.hue and args.hue in df.columns:
        violin_kwargs['hue'] = args.hue

    sns.violinplot(**violin_kwargs)

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or args.y, args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def plot_histogram(args) -> str:
    """Create histogram."""
    df = load_data(args.data, args.json)
    fig, ax = setup_figure(args.figsize, args.style, args.palette)

    hist_kwargs = {
        'data': df,
        'x': args.x,
        'kde': args.kde,
        'ax': ax
    }

    if args.bins:
        hist_kwargs['bins'] = args.bins
    if args.hue and args.hue in df.columns:
        hist_kwargs['hue'] = args.hue

    sns.histplot(**hist_kwargs)

    apply_common_options(ax, args.title, args.xlabel or args.x,
                         args.ylabel or 'Count', args.logx, args.logy, args.legend)

    return save_figure(fig, args.output, args.format, args.dpi)


def parse_figsize(value: str) -> Tuple[float, float]:
    """Parse figsize from string like '10,6'."""
    parts = value.split(',')
    return (float(parts[0]), float(parts[1]))


def add_common_args(parser: argparse.ArgumentParser):
    """Add common arguments to parser."""
    parser.add_argument('--data', '-d', help='Path to CSV/TSV/JSON data file')
    parser.add_argument('--json', '-j', help='JSON string with data')
    parser.add_argument('--output', '-o', default='plot.png', help='Output file path')
    parser.add_argument('--format', '-f', default='png', choices=['png', 'svg', 'pdf'],
                        help='Output format')
    parser.add_argument('--title', '-t', help='Plot title')
    parser.add_argument('--xlabel', help='X-axis label')
    parser.add_argument('--ylabel', help='Y-axis label')
    parser.add_argument('--figsize', type=parse_figsize, default=(10, 6),
                        help='Figure size as width,height')
    parser.add_argument('--style', default='whitegrid',
                        choices=['white', 'dark', 'whitegrid', 'darkgrid', 'ticks'])
    parser.add_argument('--palette', default='deep',
                        help='Color palette (deep, muted, bright, pastel, dark, colorblind, viridis, etc.)')
    parser.add_argument('--dpi', type=int, default=150, help='Output resolution')
    parser.add_argument('--legend', help='Legend position (upper right, lower left, etc.)')
    parser.add_argument('--logx', action='store_true', help='Log scale X-axis')
    parser.add_argument('--logy', action='store_true', help='Log scale Y-axis')


def main():
    parser = argparse.ArgumentParser(
        description='Scientific data visualization',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Plot type')

    # Line plot
    line_parser = subparsers.add_parser('line', help='Line plot')
    add_common_args(line_parser)
    line_parser.add_argument('--x', required=True, help='X-axis column')
    line_parser.add_argument('--y', required=True, help='Y-axis column(s), comma-separated')
    line_parser.add_argument('--hue', help='Color grouping column')
    line_parser.add_argument('--line-style', help='Line style column')
    line_parser.add_argument('--markers', action='store_true', help='Add markers')

    # Scatter plot
    scatter_parser = subparsers.add_parser('scatter', help='Scatter plot')
    add_common_args(scatter_parser)
    scatter_parser.add_argument('--x', required=True, help='X-axis column')
    scatter_parser.add_argument('--y', required=True, help='Y-axis column')
    scatter_parser.add_argument('--hue', help='Color grouping column')
    scatter_parser.add_argument('--size', help='Size column')
    scatter_parser.add_argument('--alpha', type=float, default=0.7, help='Point transparency')

    # Bar chart
    bar_parser = subparsers.add_parser('bar', help='Bar chart')
    add_common_args(bar_parser)
    bar_parser.add_argument('--x', required=True, help='Category column')
    bar_parser.add_argument('--y', required=True, help='Value column')
    bar_parser.add_argument('--hue', help='Color grouping column')
    bar_parser.add_argument('--horizontal', action='store_true', help='Horizontal bars')
    bar_parser.add_argument('--error', help='Error bar column')

    # Heatmap
    heatmap_parser = subparsers.add_parser('heatmap', help='Heatmap')
    add_common_args(heatmap_parser)
    heatmap_parser.add_argument('--cmap', default='viridis', help='Color map')
    heatmap_parser.add_argument('--annotate', action='store_true', help='Show values')
    heatmap_parser.add_argument('--cluster', action='store_true', help='Cluster rows/columns')

    # Box plot
    box_parser = subparsers.add_parser('box', help='Box plot')
    add_common_args(box_parser)
    box_parser.add_argument('--x', help='Grouping column')
    box_parser.add_argument('--y', required=True, help='Value column')
    box_parser.add_argument('--hue', help='Color grouping column')

    # Violin plot
    violin_parser = subparsers.add_parser('violin', help='Violin plot')
    add_common_args(violin_parser)
    violin_parser.add_argument('--x', help='Grouping column')
    violin_parser.add_argument('--y', required=True, help='Value column')
    violin_parser.add_argument('--hue', help='Color grouping column')
    violin_parser.add_argument('--split', action='store_true', help='Split violins by hue')

    # Histogram
    hist_parser = subparsers.add_parser('histogram', help='Histogram')
    add_common_args(hist_parser)
    hist_parser.add_argument('--x', required=True, help='Value column')
    hist_parser.add_argument('--bins', type=int, help='Number of bins')
    hist_parser.add_argument('--kde', action='store_true', help='Add KDE line')
    hist_parser.add_argument('--hue', help='Color grouping column')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'line':
            plot_line(args)
        elif args.command == 'scatter':
            plot_scatter(args)
        elif args.command == 'bar':
            plot_bar(args)
        elif args.command == 'heatmap':
            plot_heatmap(args)
        elif args.command == 'box':
            plot_box(args)
        elif args.command == 'violin':
            plot_violin(args)
        elif args.command == 'histogram':
            plot_histogram(args)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
