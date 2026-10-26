"""Reserve for a short 5V trial and automatic return, not a long stress test."""


def short_trial_reserve(capacity, remaining_uah, sample):
    if type(capacity) is not int or type(remaining_uah) is not int:
        return False
    if not 10 <= capacity <= 100 or remaining_uah < 120000:
        return False
    if not (sample['shadow'] == 0 and sample['valid'] == sample['online'] == sample['protection_ok'] == 1):
        return False
    if any(sample[k] for k in ['fault', 'error', 'stop_error', 'latched', 'cycle_timeout',
                             'thermal_inhibit', 'source_inhibit', 'gauge_charge_stop']):
        return False
    return (sample['budget_ua'] == 500000 and sample['desired_enable'] == 1
            and sample['gauge_current_ua'] > 0 and 180 <= sample['temp_decic'] < 400
            and min(sample['cell1_uv'], sample['cell2_uv']) >= 3700000
            and max(sample['cell1_uv'], sample['cell2_uv']) <= 4375000
            and abs(sample['cell1_uv'] - sample['cell2_uv']) <= 30000)
