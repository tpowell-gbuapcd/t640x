# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:37:46 2020

@author: twpow
"""

from time import strptime
from datetime import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates 
import numpy as np
import re, os, sys

file = 'C:/Users/twpow/OneDrive/Desktop/python/AV_lee_vining.txt'
error = -999999999991

def get_param_names(params):
    '''
    Get names of parameters from the header of the text document, trim off unnecessary characters
    
    input param: params, the header of the text file as a list split by the ',' character
    input type: list
    
    return: params, list of names from text document without unecessary characters. Entries become the 
    keys of the dictionary. 
    return type: list of strings
    '''
    
    counter = 0
    rmv_chars = [' ', '\n']
   
    while counter != len(params):
        for char in rmv_chars:
            if char in params[counter]:
                params[counter] = params[counter].replace(char, '')
        counter += 1

    return params


def dict_init(params, length):
    '''
    initialize dictionary containing all the data. Creates the required size arrays for each data parameter
    and initializes each entry to zero.
    
    input param: params, the keys of the dictionary. These are the data names presented in the header
    of the text file. 
    input type: list
    
    input param: length, how many data entries there are (simply the length of the file)
    input type: int
    
    return: data_dict, dictionary where the keys are the names of the parameters
    return type: dictionary of arrays
    '''
    data_dict = {}
    for name in params:
        data_dict[name] = np.zeros(length)
    
    return data_dict
    

def remove_params(raw):
    '''
    Remove indices containing time parameters from the numpy array. Return just data.
    
    input param: raw, the raw data from the text file.
    input type: array
    
    return: new array with only data
    return type: array
    '''
    
    return np.delete(raw, [0,1])
    

def write_arrays(str_data):
    '''
    Take in an array where each index is a string, split the string into indivdual
    data points, and put them into a 2-d array where each element is an array
    of length n, and each element is a data point at a particular time. At the 
    same time, create an array of the indices where the ' -----' string occurs,
    indicating an I/O issue with the T640.
    
    input param: str_data, an array of strings that contain all of the data entries.
    input type: array
   
    return: raw_data, a 2-d array of all of the data found in the text document.
    return: bad_ind, a 1-d array of all of the indices where ' -----' occurs.
    '''
    
    bad_ind = np.zeros(0)
    temp = re.split(',', str_data[0])
    raw_data = np.zeros((len(str_data), len(temp)), dtype=object)
    ind = 0
    
    for val in str_data:
        temp = re.split(',', val)
        #print(temp)
        for i in range(len(temp)):
            if i == 0 or i == 1:
                #dates and times
                if temp[i][0] == ' ':
                    temp[i] = temp[i][1:]
                    raw_data[ind][i] = datetime.strptime(temp[i], '%m/%d/%Y %H:%M:%S')
                else:
                    raw_data[ind][i] = datetime.strptime(temp[i], '%m/%d/%Y %H:%M:%S')
            elif i == 19:
                #the only True/False element
                raw_data[ind][i] = bool(temp[i])
            else:
                #bad data
                if temp[i] == ' -----' or temp == '-----':
                    raw_data[ind][i] = error
                    bad_ind = np.append(bad_ind, ind)
                else:
                    #everything else
                    raw_data[ind][i] = float(temp[i])
                
        ind += 1
    
    return raw_data, bad_ind
    
  
def write_dict(params, raw):
    '''
    Create the dictionary of data, use params as key for dictionary.
    return data, dicitonary of all of the data represented in the text document
    where the keys are the names of the parameters defined at the beginning 
    of the text document.
    
    input param: params, the array of keys needed to sort data into the dictionary.
    input type: array
    
    input param: raw, the raw data from the text file.
    input type: array
    
    return data, dictionary of data where keys are parameters
    rtype: dictionary
    '''
    
    data = dict_init(params, len(raw))
    
    ind = 0
    for key in params:

        data[key] = raw[:, ind][:]
        ind += 1
        
    return data
    

def find_missing_times(time_arr):
    '''
    For missing minute data. Using the timestamps and a known interval, determine where 
    there are any data gaps. 
    
    input param: time_arr, an array of the timestamps from the data file. 
    input type: array
    
    return: missing, an array of the missing times
    return: start_missing, an array of the beginning timestamp for a block of missing time
    return: diff, an array of the length of the a block of missing time
    return: dates, an array of dates that have occurrences of missing time. 
    '''
    missing = np.zeros(0, dtype=object)
    start_missing = np.zeros(0, dtype=object)
    dates = np.zeros(0, dtype=object)
    diff = np.zeros(0)
    delta = timedelta(seconds=60)
    i = 1
    
    while i != len(time_arr):
        if time_arr[i] != time_arr[i-1]+delta:
            start = time_arr[i-1]
            end = time_arr[i]
            time_diff = (end - start).seconds//60
            
            # dates contains all the dates where there are missing times
            if start.date() not in dates:
                dates = np.append(dates, start.date())
                
            # diff represents the amount of time missed in minutes
            diff = np.append(diff, time_diff)
            # start_missing is the last time recorded in a block of missing times
            start_missing = np.append(start_missing, start)            
            
            # populates an array with the missing times
            while start != end and start < end:
                start += delta
                missing = np.append(missing, start)
            
        i += 1

    return missing, start_missing, diff, dates


def find_stuck_data(data_dict, arr):
    '''
    Sort throught the data and find instances where the data are "stuck" on the same values.
    Return datasets that can be used to generate statistics on the severity of stuck data.
    Important for assessing how badly the T640x issues are impacting data. 
    
    input param: data_dict, dictionary of data where keys are parameters
    input type: dictionary
    
    input param: arr, array of raw data without timestamps
    input type: array
    
    return: repeat_vals, array of the index of a repeating value
    return: repeat_counts, array of the number of repeating counts (a block of repeated data) ?
    return: running_count, array of the length of a block of repeated data
    '''

    # very slow, takes several minutes, should be cleaned up if this code is to be used 
    # more frequently. Although, the slowness is definitely due to the machine it was
    # written on. 
    # creates strings from each line for comparison
    count = 0
    new_count = 0
    data_str = ''
    rmv_chars = [' ', '\n']
    
    comp_str = np.full(len(arr), fill_value='', dtype=object)
    repeat_vals = np.zeros(0, dtype=int)
    repeat_counts = np.zeros(0, dtype=int)
    running_count = np.zeros(0, dtype=int)
    
    for val in arr:
        
        # counter = 2 to avoid times
        # count is the index of the repeat value.
        counter = 2
        previous = data_str
        data_str = ''
        temp = re.split(',', val)
        
        # contruct string for comparison, remove spaces and new line characters
        for val in temp[2:]:
            for char in rmv_chars:
                if char in val:
                    val = val.replace(char, '')
            temp[counter] = val
            counter += 1     
        
        data_str = ''
        data_str = data_str.join(temp[2:])
        comp_str[count] = data_str
        
        if count > 0:
            if previous == data_str:
                if new_count == 0:
                    repeat_vals = np.append(repeat_vals, int(count-1))
                    running_count = np.append(running_count, new_count+1)
                else:
                    repeat_vals = np.append(repeat_vals, int(count-1))
                    running_count = np.append(running_count, new_count+1)
                new_count += 1
            else:
                if new_count > 0:
                    repeat_vals = np.append(repeat_vals, int(count-1))
                    repeat_counts = np.append(repeat_counts, new_count+1)
                    running_count = np.append(running_count, new_count+1)

                new_count = 0
        
        count += 1

    return repeat_vals, repeat_counts, running_count
    
            
def plot_data(data_dict, ind):
    '''
    Plot how many instances of '-----' per day occur over the timeframe of the
    data set.
    '''
    
    start = data_dict['Date&Time(Local)'][0].date()
    end = data_dict['Date&Time(Local)'][-1].date()
    
    temp = np.zeros(0)
    for val in ind:
         temp = np.append(temp, data_dict['Date&Time(Local)'][int(val)].date())
        
    bad_dates, bad_counts = np.unique(temp, return_counts=True)
    
    text = ''
    for i in range(len(bad_counts)):
        if bad_counts[i] != 0:
            text += 'Counts = {}, Date = {}\n'.format(bad_counts[i], bad_dates[i].strftime('%m/%d/%Y'))
    
    fig, ax = plt.subplots(figsize=(5,5))
    ax.bar(bad_dates, bad_counts)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
    ax.set_title("Lee Vining T640x ' -----' Data Entries")
    ax.set_xlabel("Date")
    ax.set_ylabel("# of Bad Entries")
    ax.set_xlim(start, end)
    ax.text(1.03, 1.0, text, transform=ax.transAxes, verticalalignment='top', 
            bbox=dict(facecolor='black', alpha=0.1))
    ax.xaxis_date()
    ax.grid(True)
    plt.setp(ax.get_xticklabels(), rotation = 45)
    
    plt.savefig("Lee Vining T640x Bad Data.jpg", bbox_inches='tight')
    plt.tight_layout()
    plt.show

    return bad_counts, bad_dates
    
    
def plot_missing_times(data_dict, missing, diff, dates):
    
    start = data_dict['Date&Time(Local)'][0].date()
    end = data_dict['Date&Time(Local)'][-1].date()
    bins = 50
    
    text = ''
    date_text = 'Dates with Missing Time:\n'
    unique_vals, unique_counts = np.unique(diff, return_counts=True)
    
    for val, count in zip(unique_vals, unique_counts):
        text += "Minutes Lost: {}, Counts: {}\n".format(val, count)
    
    for date in dates:
        date_text += date.strftime('%m/%d/%Y') + '\n'
    
    fig, (ax, ax_hist) = plt.subplots(2,1, figsize=(10,10))
    ax.bar(missing, diff)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
    ax.set_xlim(start, end)
    ax.xaxis_date()
    ax.set_title("Lee Vining T640x Missing Minutes")
    ax.set_xlabel("Date")
    ax.set_ylabel("Minutes")
    ax.text(1.05, 1.00, date_text, transform=ax.transAxes, verticalalignment='top')
    ax.grid(True)
    plt.setp(ax.get_xticklabels(), rotation = 45)
    
    ax_hist.hist(diff, bins)
    ax_hist.grid(True)
    ax_hist.set_title("Lee Vining T640x Missing Minutes")
    ax_hist.set_xlabel("Minutes Missed")
    ax_hist.set_ylabel("Counts")
    ax_hist.text(1.05, 1.00, text, transform=ax_hist.transAxes, verticalalignment='top')
    
    plt.tight_layout()
    plt.savefig("Lee Vining T640x Missing Data.jpg", bbox_inches='tight')
    plt.show()

    
def print_stats(data_dict, bad_counts, bad_dates):
    
    bad_keys = np.zeros(0, dtype=str)
    
    for key in data_dict:
        for val in data_dict[key]:
            if val == error:
                if key not in bad_keys:
                    bad_keys = np.append(bad_keys, key)
                #print(key)
    
    for val in bad_keys:
        print('Bad data occurs in {}'.format(val))
    
    print('\n')
    
    for i in range(len(bad_counts)):
        if bad_counts[i] != 0:
            print('{} instances of bad data on {}'.format(bad_counts[i], bad_dates[i].strftime('%m/%d/%Y')))
    
    
def plot_stuck_times(data_dict, time, counts, diff):
    
    # this is all bad code. I should be ashamed. But it works, so good for me.
    start = data_dict['Date&Time(Local)'][0].date()
    end = data_dict['Date&Time(Local)'][-1].date()
    
    time_arr = np.zeros(len(time), dtype=object)
    date_arr = np.zeros(len(data_dict['Date&Time(Local)']), dtype=object)
    
    i=0
    for i in range(len(time)):
        #gives me an array of timestamps of stuck times concatenated to just date
        time_arr[i] = data_dict['Date&Time(Local)'][time[i]].date()
    
    number_of_daily_timestamps = 60*24
    
    all_dates, all_counts = np.unique(date_arr, return_counts=True)
    stuck_dates, stuck_counts = np.unique(time_arr, return_counts=True)
    unique_counts, counts_counts= np.unique(counts, return_counts=True)
    
    perc_loss_date = np.zeros(len(stuck_dates))
    perc_counts = np.zeros(len(counts_counts))
    stuck_loss = np.zeros(len(counts_counts))
    
    #array of percentages showing the percentage of daily data that is stuck
    for i in range(len(stuck_dates)):
        perc_loss_date[i] = stuck_counts[i]/number_of_daily_timestamps*100
       
    
    for i in range(len(perc_counts)):
        tot= np.sum(counts_counts)
        perc_counts[i] = counts_counts[i]/tot*100.0
        stuck_loss[i] = counts_counts[i]/len(time)*100.0
    
    #this plot will probably be better visuallized as a percentage of the 
    #data for each day that is stuck
    
    fig, (ax, ax_2) = plt.subplots(2,1, figsize=(10,10))
    ax.bar(stuck_dates, perc_loss_date)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
    ax.set_xlim(start, end)
    ax.xaxis_date()
    ax.set_title("Lee Vining T640x Stuck Minutes")
    ax.set_xlabel("Date")
    ax.set_ylabel("Percentage of daily date stuck (%)")
    #ax.text(1.05, 1.00, date_text, transform=ax.transAxes, verticalalignment='top')
    ax.grid(True)
    plt.setp(ax.get_xticklabels(), rotation = 45)
    
    ax_2.bar(unique_counts, perc_counts)
    ax_2.set_title("Stuck Data Percentage")
    ax_2.set_xlabel("Concurrent Timestamps in Minutes That Are Stuck")
    ax_2.set_ylabel("Percent (%)")
    ax_2.grid(True)
    plt.tight_layout()
    plt.savefig("Lee Vining T640x Stuck Data.jpg", bbox_inches='tight')
    plt.show()
    
    
       
with open(file, 'r') as datafile:
    
    print(datetime.now())
    lines = np.array(datafile.readlines())
    p = re.split(',', lines[0])
    parameters = get_param_names(p)
    str_array = remove_params(lines)
    
    raw_array, bad_index = write_arrays(str_array)
    data = write_dict(parameters, raw_array)
    stuck_vals, stuck_counts, count_counter = find_stuck_data(data, str_array)
    plot_stuck_times(data, stuck_vals, stuck_counts, count_counter)
    datafile.close()
    
    missing_times, start_missing, diff_times, missing_dates = find_missing_times(data['Date&Time(Local)'])
    plot_missing_times(data, start_missing, diff_times, missing_dates)
    counts, dates = plot_data(data, bad_index)
    print_stats(data, counts, dates)
    print(datetime.now())
    
    '''
    #code that may come in handy
    
    #Date&Time(Local)
    #Date&Time(UTC)
    
    #shows that the issue only occurs with concentration measurements.
    #PM10Conc, PM10-2.5Conc, PM10STPConc, PM2.5Conc
    for key in data_dict:
        for val in data_dict[key]:
            if val == error:
                print(key)
                   
    delta = timedelta(days=1)
    current = start
    while current != (end+delta):
        if current not in bad_dates:
            bad_counts = np.append(bad_counts, 0)
            bad_dates = np.append(bad_dates, current)
        current += delta
    
    '''
