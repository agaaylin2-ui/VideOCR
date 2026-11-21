# Preview 5 multilingual OCR validation

The AMD desktop exports one language per run. Choose **English**, **Chinese** (Simplified by default), or **Chinese Traditional**. Their suggested filenames end in `.en.srt`, `.zh-Hans.srt`, and `.zh-Hant.srt`. A narrow crop helps when a scene contains dialogue and credits in the same language.

## What the language setting controls

In [upstream VideOCR at 548f875](https://github.com/timminator/VideOCR/tree/548f8753d169539e56a0fb4ba532a53d8b7a8c82), the GUI maps those three names to `en`, `ch`, and `chinese_cht`. The API calls `resolve_model_dirs`. For all three codes it selects `PP-OCRv6_small_det` and `PP-OCRv6_small_rec` with the default model setting. The detection pass receives the detector path. The native OCR command receives the language code and both explicit model paths. Other languages have their own lookup rules.

Upstream accepts regions over the confidence threshold, groups them by vertical overlap, and orders the text by line and horizontal position. The optional Simplified conversion, language-specific word spacing, and voting across similar frames operate on that assembled text. On the bilingual dialogue sample, native CPU exports for all three settings included both lines.

[Preview 4 at 9c23a34](https://github.com/aylinlabs/VideoOCR-AMD/tree/9c23a34ca24150ed2ed0a84aeac68a74b6bef07a) additionally restricted the desktop dropdown and queued-job editor to English, overwrote the selected language when building the job, and rejected other codes in the DirectML API. Its PaddleX worker supplies the verified model directories and decoder configuration explicitly. Changing the language passed to the worker alone cannot separate the lines.

## Selection and ambiguity

Preview 5 selects text after confidence filtering and line ordering, before frame similarity, voting and SRT generation. Each selected region keeps its original box and confidence. English uses Latin script as evidence and both Chinese settings use Han script. This is a rule for English/Chinese bilingual material. It cannot identify English among multiple Latin-script languages.

- Either vertical order works. Opposite-script boxes on one line can be selected independently. A detached number or punctuation mark follows the nearest scripted box. Standalone numeric cues and ellipses can appear in both exports.
- A single OCR box can contain two translations. Split on a clear phrase boundary when the two sides have different host scripts. A long Han passage joined to a substantial Latin phrase can also be separated without punctuation. Short embedded names and acronyms stay intact. For ambiguous text surrounded by one script, keep the entire phrase with that script. For a single unresolved switch, three or more Latin words favor English, otherwise favor Chinese. A short foreign-script box tightly enclosed by two same-script neighbors follows the enclosing sentence. These rules can misclassify short translations and long proper names.
- Nearby bilingual lines with similar horizontal centers identify the dialogue column. This can exclude distant credits without assuming English appears first or requiring a fixed screen position. Exact preview labels, role headers and groups of narrow vertical credit columns receive additional filtering. Horizontal company names, logos, or scene text inside the subtitle region can still pass.
- **Chinese** honors the existing Simplified normalization setting. **Chinese Traditional** uses the bundled OpenCC dictionary to render recognized Han text in Traditional characters. A conversion cannot recover the original spelling when the recognizer has collapsed a distinction. The optional word splitter leaves selected mixed-script cues intact so it cannot insert spaces inside a name or time.
- Cue boundaries follow the frames where the selected text survives. Two translations can appear at different times. The frame timestamps, merge-gap setting, minimum duration, crop and zone handling use the Preview 4 implementation.

## Matched-frame comparison

Tested on Windows 11 and the RX 9070 XT with the supplied bilingual episode and its existing English-named SRT. For 04:02–04:11, all runs used the default bottom region, center alignment, 720-pixel maximum OCR width, frame skip 1, confidence 75%, SSIM 94%, similarity 80%, merge gap 0.1 s and minimum cue duration 0.2 s. Word post-processing was off. The original CPU test called upstream's video and subtitle methods with the cached native PaddleOCR CPU v3.7.0 executable. The isolated comparison copy deferred the optional CPUID import used by its launcher hardware check.

All seven runs used identical image bytes in identical order. The six stitched detection inputs yielded 131 polygons. The 47 recognition inputs yielded 91 region predictions. Every polygon and recognized string matched across upstream CPU, Preview 4 DirectML, and Preview 5 DirectML. The largest absolute native/DirectML score difference was 0.000033 for detection and 0.000011 for recognition. For example, the first dialogue frame contained these two distinct regions.

| Region | Polygon | Native confidence | Preview 4 DirectML confidence |
| --- | --- | ---: | ---: |
| That brat is right inside! | (266,40), (452,41), (452,63), (266,61) | 0.962431 | 0.962421 |
| 那小子就在里面 | (297,66), (421,66), (421,86), (297,86) | 0.999897 | 0.999897 |

| Export | Four reference dialogue cues | Timing |
| --- | --- | --- |
| Upstream CPU, each of the three settings | Both languages in all four cues | 4/4 matched the supplied SRT |
| Preview 4 DirectML, English | Both languages in all four cues | 4/4 matched |
| Preview 5 DirectML, English | Only the four English lines | 4/4 matched |
| Preview 5 DirectML, Chinese | Only the four Chinese lines, in Simplified characters | 4/4 matched |
| Preview 5 DirectML, Chinese Traditional | Only the four Chinese lines, including 來的夠快的 | 4/4 matched |

Both models used the existing PP-OCRv6 small exports. The detector ONNX SHA-256 was `b1a4f07289eda88d29239890b94ea2f9e29f5635a33ff6e165bb1b27dcea25fc`. The recognizer SHA-256 was `7a10319171913a664e03b9f84bb159dbc1c7c397a2ff7a79d89287df64c64d4b`. The native and exported detector configurations matched byte-for-byte, as did the recognition configurations. On the short excerpt the sampled detector recorded 157 DirectML node events. The recognizer recorded 489 DirectML events and six CPU events for Slice and Concat.

## Episode results and limitations

The 22:16 bilingual episode ran with three DirectML workers in both passes. For a controlled comparison the validation harness assembled the three target tracks and a Preview 4-style unfiltered track from the same predictions. Each language also ran independently through the DirectML exporter on the four-cue excerpt.

| Full episode track | Total cues | Cues containing both ASCII letters and Han characters |
| --- | ---: | ---: |
| Supplied English-named SRT | 535 | 450 |
| Unfiltered assembly from the controlled run | 532 | 450 |
| Preview 5 English | 466 | 0 |
| Preview 5 Simplified Chinese | 565 | 3 |
| Preview 5 Traditional Chinese | 564 | 3 |

The English track contained no Han characters. The three mixed Chinese cues contained TV or SVIP in company or promotional text. These counts measure script separation. They do not measure transcription accuracy or prove that every remaining cue is dialogue. In the opening song, selection removed off-center Chinese credit names beside the lyrics. An OCR mistake in the English lyric, including a musical note read as a letter, survived. In the end cards, OCR sometimes fused an English caption to a long Chinese passage and misread spacing or punctuation. The new split separates the two scripts but cannot repair those recognition errors.

Between 04:02 and 07:30, 51 supplied cues contained exactly one English line followed by one Chinese line. At the reference cue midpoint, the English track matched 51/51 strings and the Simplified track matched 50/51. The remaining Chinese line appeared 40 ms after the reference midpoint and matched the text. Exactly 49 English and 38 Chinese cues also had both reference endpoints. A visual check of the latter example showed English alone at 06:16.400 and both lines at 06:17.000. Sampling and the original recognition thresholds still limit timing precision.

The separate 21:30 Preview 4 reference produced 368 cues and consisted mostly of Chinese. Reassembling the corresponding real GPU results with the final Chinese selector produced 366 cues. 358 had both original endpoints and 349 matched both text and endpoints. Both replayed OCR passes verified the ordered JPEG hashes before using recorded predictions. The changed cues and episode-end credits merit human review.

## Repeat the regression checks

Run `python -m unittest discover -s tests -v` with the desktop runtime. Enable the existing Windows hardware test with `VIDEOCR_TEST_AMD_VIDEO=1` and the prepared model/runtime folders described in [console testing](AMD_VIDEO_WINDOWS.md). The suite passed all 28 tests with that check enabled. The small fixtures cover both line orders, same-row and single-box translations, monolingual frames, blank intervals, credits, names, punctuation, digits and Traditional forms.

Run `python tests/desktop_acceptance.py PATH_TO_PACKAGED_APP` with the packaged Windows runtime to exercise the actual GUI and worker process. A separate test bundle passed two cropped, queued exports in different languages, cancellation, and language restoration after reopening. Human review should include native Traditional footage and dialogue over credits. The supplied episode principally demonstrates Simplified source text and Traditional rendering.
