// FlowChart.js
function FlowChart({ blocks, jsPlumbInstance, onEdit, onVerify }) {
  const containerRef = React.useRef(null);
  
  React.useEffect(() => {
    if (!containerRef.current) return;
    
    setTimeout(() => {
      jsPlumbInstance.setContainer(containerRef.current);
      jsPlumbInstance.deleteEveryEndpoint();
      
      blocks.forEach(block => {
        const element = document.getElementById(`block-${block.id}`);
        if (element) {
          jsPlumbInstance.revalidate(element);
        }
      });
    }, 100);
  }, [blocks, jsPlumbInstance]);
  
  return (
    <div ref={containerRef} className="flowchart-container">
      {blocks.map(block => (
        <Block 
          key={block.id} 
          block={block} 
          jsPlumbInstance={jsPlumbInstance}
          onEdit={onEdit}
          onVerify={onVerify}
        />
      ))}
    </div>
  );
}