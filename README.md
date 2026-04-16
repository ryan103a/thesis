# Thesis
Undergraduate thesis work. Generating a stereo event camera dataset for underwater applications.

## Event camera output

Prophesee metavision [viewer](https://docs.prophesee.ai/stable/samples/modules/stream/viewer.html#chapter-samples-stream-viewer). Allows for streaming and recording of camera data.

## Event camera calibration files

### Biases

Adjusting biases [link](https://docs.prophesee.ai/stable/hw/manuals/biases.html#chapter-biases). Includes information about the bais settings and what they do, as well as the limits for the EVK4-HD model. An example file for biases is `camera_settings.json`

```
{
 "ll_biases_state": {
  "bias": [
   {
    "name": "bias_diff",
    "value": 0
   },
   {
    "name": "bias_diff_on",
    "value": 0
   },
   {
    "name": "bias_diff_off",
    "value": 0
   },
   {
    "name": "bias_fo",
    "value": 0
   },
   {
    "name": "bias_hpf",
    "value": 0
   },
   {
    "name": "bias_refr",
    "value": 0
   }
  ]
 }
}
```


## Event camera calibration 

Prophesee [focus adjustment](https://docs.prophesee.ai/stable/samples/modules/calibration/focus.html#chapter-samples-calibration-focus) and [calibration](https://docs.prophesee.ai/stable/samples/modules/calibration/calibration_pipeline.html#chapter-samples-calibration-calibration-pipeline) pages. Requires the Metavision SDK (don't currently have). 
