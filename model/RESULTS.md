# Our model · evaluation

The active `skillcorner_20_compact` model trains on all 20 SkillCorner matches with
121 dead-ball and 108 possession inputs. Full fit time: 184.70 seconds.

| Evaluation | spellF1 | macroF1 |
| --- | ---: | ---: |
| Training, 20 matches (in-sample mean) | 0.8019 | 0.9392 |
| Held-out, 4 matches (16-match retrain) | 0.7287 | 0.9198 |
| Barcelona public five minutes | 0.6065 | 0.8963 |

Barcelona contains 7,500 scored frames, 17 reference possessions, and 14 predicted possessions.
The latest centroid-smoothing removal preserves Barcelona spellF1 and increases macroF1
from 0.8929 to 0.8963. Its predictions differ from earlier checkpoints.

Simplification removes exact duplicate inputs, seven globally unused features, four
classifier-specific unused inputs, and the own/opponent one- and three-second centroid averages.
Raw centroids and spread, ball-position, and distance-advantage smoothing remain.

See [active model provenance](reports/training.json),
[held-out validation details](reports/validation.json), and [method and limitations](README.md).
Historical experiment code and checkpoints are excluded from this focused repository.

SkillCorner labels are provider-derived weak labels. The four-match holdout and Barcelona
public window have been reused; small score changes do not establish general improvement.
Barcelona labels never enter fitting. The second-half kickoff rule is unchanged.
