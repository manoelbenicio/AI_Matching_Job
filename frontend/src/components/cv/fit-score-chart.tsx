'use client';

/**
 * FitScoreChart — animated donut gauge showing CV fit score
 * with matched/missing skill breakdown.
 * Pure SVG, no chart library.
 */

interface FitScoreChartProps {
    fitScore: number;
    matchedCount: number;
    missingCount: number;
}

export function FitScoreChart({ fitScore, matchedCount, missingCount }: FitScoreChartProps) {
    const total = matchedCount + missingCount;
    const matchedPct = total > 0 ? Math.round((matchedCount / total) * 100) : 0;

    // SVG donut math
    const size = 140;
    const cx = size / 2;
    const cy = size / 2;
    const radius = 54;
    const strokeWidth = 10;
    const circumference = 2 * Math.PI * radius;
    const scoreOffset = circumference - (fitScore / 100) * circumference;

    const level =
        fitScore >= 85 ? 'excellent' :
            fitScore >= 70 ? 'great' :
                fitScore >= 55 ? 'good' :
                    fitScore >= 35 ? 'partial' : 'weak';

    const colorMap: Record<string, string> = {
        excellent: '#22c55e',
        great: '#3b82f6',
        good: '#eab308',
        partial: '#f59e0b',
        weak: '#ef4444',
    };

    const color = colorMap[level];

    return (
        <div className="fit-chart">
            <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                className="fit-chart__svg"
            >
                {/* Background ring */}
                <circle
                    cx={cx}
                    cy={cy}
                    r={radius}
                    fill="none"
                    stroke="rgba(255,255,255,0.06)"
                    strokeWidth={strokeWidth}
                />
                {/* Score arc */}
                <circle
                    cx={cx}
                    cy={cy}
                    r={radius}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={scoreOffset}
                    style={{
                        transform: 'rotate(-90deg)',
                        transformOrigin: 'center',
                        transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                />
                {/* Center text */}
                <text
                    x={cx}
                    y={cy - 6}
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="fit-chart__score-text"
                    fill={color}
                >
                    {fitScore}
                </text>
                <text
                    x={cx}
                    y={cy + 14}
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="fit-chart__label-text"
                >
                    FIT SCORE
                </text>
            </svg>

            {/* Legend */}
            <div className="fit-chart__legend">
                <div className="fit-chart__legend-item">
                    <span className="fit-chart__dot fit-chart__dot--matched" />
                    <span className="fit-chart__legend-label">Matched</span>
                    <span className="fit-chart__legend-value">{matchedCount} ({matchedPct}%)</span>
                </div>
                <div className="fit-chart__legend-item">
                    <span className="fit-chart__dot fit-chart__dot--missing" />
                    <span className="fit-chart__legend-label">Missing</span>
                    <span className="fit-chart__legend-value">{missingCount} ({total > 0 ? 100 - matchedPct : 0}%)</span>
                </div>
            </div>
        </div>
    );
}
