"""The supported training path fits both classifiers and preserves team symmetry."""
import numpy as np
from threadpoolctl import threadpool_limits
from model.core.classifiers import Stage1


def test_fit_and_symmetric_inference():
    rng = np.random.default_rng(0)
    labels = np.repeat(['H', 'A', 'D'], 80)
    own = np.where(labels == 'H', 1., 10.) + rng.uniform(0, .2, len(labels))
    opp = np.where(labels == 'A', 1., 10.) + rng.uniform(0, .2, len(labels))
    features = {
        'team': {0: {'own_d': own, 'opp_d': opp, 'd_diff': own - opp},
                 1: {'own_d': opp, 'opp_d': own, 'd_diff': opp - own}},
        'shared': {'ball_speed': np.where(labels == 'D', 0., 5.)},
        'fps': 25,
    }
    swapped = dict(features, team={0: features['team'][1], 1: features['team'][0]})
    with threadpool_limits(limits=2):
        model = Stage1(gb_params={'max_iter': 3, 'min_samples_leaf': 4}, stride=1).fit([(features, labels)])
        dead, home = model.predict(features)
        swapped_dead, swapped_home = model.predict(swapped)
    assert model.dead.n_iter_ == model.poss.n_iter_ == 3
    assert np.isfinite(dead).all() and np.isfinite(home).all()
    np.testing.assert_allclose(dead, swapped_dead)
    np.testing.assert_allclose(home, 1 - swapped_home)
