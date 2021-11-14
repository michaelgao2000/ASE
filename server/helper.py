import datetime as dt

def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

def convert_epoch_milliseconds_to_datetime_string(time_in_millis):
    return dt.datetime.fromtimestamp(time_in_millis / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
