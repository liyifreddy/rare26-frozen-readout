# Sequential assembly

## The question

A common way to build a pipeline is to add components one at a time, keeping each if it
helps. If that procedure is run under a strict pre-registered threshold, where does it end
up, and does the answer depend on where it starts?

## How it was measured

Components are considered in a fixed order, registered in advance: pooling, then the power
transform, then the instance-selection quantile, then the shrinkage coefficient. A
component is kept only if, on that backbone, it is detectably better in both directions
against the current stack.

The procedure was run twice on each of 11 backbones. Once from the
delivered configuration and once from a neutral one: no power transform, global average
pooling, no instance selection.

## The decision rule

The stopping rule is the two-direction threshold itself. No component is kept on a single
direction or on a point estimate.

## Results

Starting from the delivered configuration, every backbone stayed where it began. Starting
from the neutral configuration, every backbone also stayed where it began. The number of
backbones on which the two starting points converge to the same configuration is
0 of 11.

## Conclusion

At this sample size no single component change clears the two-direction bar, so the
procedure halts wherever it was initialized. Its output is determined by its input.

We report this as a negative result about the procedure. It is not evidence in favor of
the configuration we happened to start from, and we do not present it that way anywhere in
the report.

## Limitations

The order in which components are considered was fixed in advance and not varied. A
different order could in principle produce a different result, though since nothing clears
the bar from either starting point, the order is unlikely to be what determines the
outcome here.
