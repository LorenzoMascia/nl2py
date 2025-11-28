// Block.js
function Block({ block, onEdit, onVerify, jsPlumbInstance }) {
  const blockRef = React.useRef(null);
  const [showTooltip, setShowTooltip] = React.useState(false);
  const [tooltipPosition, setTooltipPosition] = React.useState({ x: 0, y: 0 });

  const blockTypeClass = {
    'data': 'block-type-data',
    'process': 'block-type-process',
    'model': 'block-type-model',
    'output': 'block-type-output'
  }[block.type] || 'block-type-process';

  React.useEffect(() => {
    if (!blockRef.current || !jsPlumbInstance) return;

    jsPlumbInstance.draggable(blockRef.current, {
      containment: 'parent',
      grid: [10, 10],
      stop: function(event) {
        const rect = blockRef.current.getBoundingClientRect();
        const parentRect = blockRef.current.parentElement.getBoundingClientRect();

        block.x = rect.left - parentRect.left;
        block.y = rect.top - parentRect.top;

        jsPlumbInstance.repaintEverything();
      }
    });

    jsPlumbInstance.addEndpoint(blockRef.current, {
      anchor: "Top",
      isSource: false,
      isTarget: true,
      endpoint: "Dot",
      paintStyle: { 
        fill: "#4CAF50", 
        radius: 7 
      },
      maxConnections: -1,
      dropOptions: { hoverClass: "hover" }
    });

    jsPlumbInstance.addEndpoint(blockRef.current, {
      anchor: "Bottom",
      isSource: true,
      isTarget: false,
      endpoint: "Dot",
      paintStyle: { 
        fill: "#4CAF50", 
        radius: 7 
      },
      connectorStyle: { 
        stroke: "#4CAF50",
        strokeWidth: 2
      },
      connectorHoverStyle: {
        stroke: "#45a049",
        strokeWidth: 3
      },
      connector: ["Bezier", { curviness: 100 }],
      maxConnections: -1,
      connectorOverlays: [
        ["Arrow", { width: 12, length: 12, location: 1 }]
      ]
    });

  }, [block, jsPlumbInstance]);

  return (
    <div 
      ref={blockRef}
      id={`block-${block.id}`}
      className="workflow-block"
      style={{ 
        left: block.x, 
        top: block.y
      }}
    >
      <div className={`block-header ${blockTypeClass}`}>
        <div className="block-title">{block.title}</div>
        <div className="block-code-status">
          {block.code && !block.code.includes('# Default code') ? (
            <i className="fas fa-check-circle code-valid"></i>
          ) : (
            <i className="fas fa-exclamation-triangle code-warning"></i>
          )}
        </div>
        <div 
          className="block-step"
          onMouseEnter={(e) => {
            setTooltipPosition({
              x: e.currentTarget.offsetLeft + e.currentTarget.offsetWidth / 2,
              y: e.currentTarget.offsetTop
            });
            setShowTooltip(true);
          }}
          onMouseLeave={() => setShowTooltip(false)}
        >
          {block.step}
          {showTooltip && (
            <div 
              className="execution-tooltip"
              style={{
                left: tooltipPosition.x,
                top: tooltipPosition.y
              }}
            >
              Execution #{block.step}
            </div>
          )}
        </div>
      </div>
      <div className="block-body">{block.description}</div>
      <div className="block-footer">
        <button className="block-button verify-button" onClick={() => onVerify(block)}>
          <i className="fas fa-check-circle"></i> Check
        </button>
        <button className="block-button edit-button" onClick={() => onEdit(block)}>
          <i className="fas fa-edit"></i> Edit
        </button>
      </div>
    </div>
  );
}