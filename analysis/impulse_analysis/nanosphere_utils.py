import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as sp
import scipy.optimize as op


hz_to_khz = 1e-3

def get_psd(sphere_z, tstep, filtered_data = [], nperseg=2**16, make_plot = False, fig=[]):

    f, zpsd = sp.welch(sphere_z, fs=1/tstep, nperseg=nperseg)

    if(len(filtered_data) > 0):
        f_filt, zpsd_filt = sp.welch(filtered_data, fs=1/tstep, nperseg=nperseg)
    else:
        f_filt = []
        zpsd_filt = []

    if(make_plot):
        if(fig):
            plt.figure(fig.number)
        else:
            plt.figure(figsize=(12,4))
        plt.subplot(1,2,1)
        plt.semilogy(f*hz_to_khz, zpsd, label="Data")
        plt.semilogy(f_filt*hz_to_khz, zpsd_filt, label="Filtered")
        plt.xlim(0, 200)
        plt.xlabel("Frequency (kHz)")
        plt.ylabel("Z PSD [V$^2$/Hz]")
        plt.ylim(np.min(zpsd), np.max(zpsd))
        plt.legend()

        plt.subplot(1,2,2)
        plt.semilogy(f*hz_to_khz, zpsd)
        plt.semilogy(f_filt*hz_to_khz, zpsd_filt)
        plt.xlim(55, 67)
        plt.xlabel("Frequency (kHz)")
        plt.ylabel("Z PSD [V$^2$/Hz]")
        plt.ylim(np.min(zpsd), np.max(zpsd))


    return f, zpsd, f_filt, zpsd_filt

def impulse_func(t, A0, A1, p0, t0, p1, omega):
    p1 = p1 % np.pi
    return A0*np.sin(omega*t + p0) + A1*np.sin(omega*(t-t0) + p1)*(t>t0)

def get_filtered_data(time, sphere_z, drive, filt_band, tstep, make_plot=False):

        b, a = sp.butter(3, filt_band, btype='bandpass', fs=1/tstep)
        filtered_data = sp.filtfilt(b, a, sphere_z)

        if(make_plot):
            plt.figure(figsize=(12,4))
            plt.plot(time, sphere_z)
            plt.plot(time, filtered_data, 'b')
            plt.plot(time, drive/np.max(drive)* np.max(sphere_z), 'orange')
            plt.show()
        
        return filtered_data

def fit_data_impulse(time, filtered_data, fit_window, p0_guess, drive=[], make_plot=False, plot_guess=False):
    
    ## fit filtered data
    fit_points_orig = (time > fit_window[0]) & (time < fit_window[1])

    ## cut out drive time
    if(len(drive) > 0 and False):
        fit_points = fit_points_orig & (np.abs(drive) < 0.5*np.max(drive))
    else:
        fit_points = fit_points_orig

    cent_time = np.mean(fit_window)
    pre_pulse = (time > fit_window[0]) & (time < cent_time)
    post_pulse = (time < fit_window[1]) & (time > cent_time)

    ## if no guess is given, then guess parameters from data
    if(len(p0_guess) == 0): 
        pre_pulse_fft = np.fft.rfft(filtered_data[pre_pulse])
        freqs = np.fft.rfftfreq(len(filtered_data[pre_pulse]), d=time[1]-time[0])

        ## buffer to search around expect peak location
        search_buff = 10e3 ## Hz
        f0_guess = 65e3 ## Hz

        ## pre pulse
        pre_pulse_fft[np.abs(freqs - f0_guess) > search_buff] = 0
        peak_pos = np.argmax(np.abs(pre_pulse_fft))
        f0_pre = freqs[peak_pos]
        norm = 1e-3 #/(time[1]-time[0])
        a0_pre = np.abs(pre_pulse_fft[peak_pos]) * norm
        p0_pre = np.angle(pre_pulse_fft[peak_pos])


        post_pulse_fft = np.fft.rfft(filtered_data[post_pulse])
        freqs = np.fft.rfftfreq(len(filtered_data[post_pulse]), d=time[1]-time[0])
        ## post pulse
        post_pulse_fft[np.abs(freqs - f0_guess) > search_buff] = 0
        peak_pos = np.argmax(np.abs(post_pulse_fft))
        f0_post = freqs[peak_pos]
        a0_post = np.abs(post_pulse_fft[peak_pos])*norm
        p0_post = np.angle(post_pulse_fft[peak_pos])

        f0_guess = np.mean([f0_pre, f0_post])

        p0_guess = [a0_pre, a0_post, p0_pre, cent_time, p0_post, 2*np.pi*f0_guess]

    impulse_func_fixed_t = lambda t, A0, A1, p0, p1, omega: impulse_func(t, A0, A1, p0, p0_guess[3], p1, omega)
    p0_guess_fixed_t = [p0_guess[0], p0_guess[1], p0_guess[2], p0_guess[3], p0_guess[5]]

    fit_failed = False
    if(not plot_guess):
        try:
            bp, _ = op.curve_fit(impulse_func_fixed_t, time[fit_points], filtered_data[fit_points], p0=p0_guess_fixed_t, maxfev=10000)
        except RuntimeError:
            print("Fit failed, plotting guess")
            fit_failed = True
            bp = p0_guess_fixed_t
    else:
        bp = p0_guess_fixed_t

    print("Fit parameters: A0 = %.2e, A1 = %.2e, p0=%.2f, p1=%.2f, f0=%.1f"%(bp[0], bp[1], bp[2], bp[3], bp[4]/(2*np.pi)) )

    if(make_plot):
        plt.figure(figsize=(12,4))
        plt.plot(time[fit_points], filtered_data[fit_points], 'b')
        if(len(drive) > 0):
            plt.plot(time[fit_points_orig], 
                     drive[fit_points_orig]/np.max(drive[fit_points_orig])* np.max(filtered_data[fit_points_orig]), 'orange')
        plt.plot(time[fit_points], impulse_func_fixed_t(time[fit_points], *bp), 'r', lw=0.5)
        plt.xlim(fit_window)
        plt.xlabel("Time [s]")
        plt.ylabel("Z position [V]")
        plt.show()

    return bp[1], fit_failed


def find_impulses(drive, make_plot=False):
     
    # find the peaks in the drive signal
    threshold = 0.5
    max_val = np.max(drive)

    pulse_idx = np.where((drive > threshold*max_val) & (np.roll(drive,-1) < threshold*max_val))[0] 

    if(make_plot):
        #plt.figure(figsize=(12,4))
        plt.plot(drive)
        plt.plot(pulse_idx, drive[pulse_idx], 'ro')
        plt.show()

    return pulse_idx

def chi(f, A, omega0, gamma):
    omega = 2*np.pi*f
    return A/(omega0**2 - omega**2 + 1j*omega*gamma)

def abs_chi2(f, A, omega0, gamma):
    omega = 2*np.pi*f
    return A*np.abs(1/(omega0**2 - omega**2 + 1j*omega*gamma))**2

def deconvolve_force_amp(time, filtered_data, fit_window, make_plot=False, f0_guess = 65e3, 
                         search_wind=10e3, gamma=1e3, cal_fac=1e-8, lp_freq=200e3, ax_list = []):

    fit_points = (time > fit_window[0]) & (time < fit_window[1])
    pow2_len = 2**int(np.log2(np.sum(fit_points)))
    cent_time = np.mean(fit_window)
    cent_time_idx = np.argmin(np.abs(time - cent_time)) 
    if(cent_time_idx + int(pow2_len/2)+1 > len(time) or cent_time_idx - int(pow2_len/2) < 0):
        return -1, -1, -1, -1, -1
    fit_points = (time > time[cent_time_idx - int(pow2_len/2)]) & (time < time[cent_time_idx + int(pow2_len/2)+1])

    curr_time = time[fit_points]
    curr_filtered_data = filtered_data[fit_points]
    cent_time_idx = np.argmin(np.abs(curr_time - cent_time))


    data_fft = np.fft.rfft(curr_filtered_data)
    freqs = np.fft.rfftfreq(len(curr_filtered_data), d=time[1]-time[0])

    data_fft_for_search = np.abs(data_fft)
    data_fft_for_search[np.abs(freqs - f0_guess) > search_wind] = 0
    f0 = freqs[np.argmax(data_fft_for_search)]
    omega0 = 2*np.pi*f0

    pts_to_use = np.abs(freqs - f0) < search_wind
    spars = [(np.max(np.abs(data_fft[pts_to_use])*omega0*gamma)**2), omega0, gamma]
    try:
        bp, _ = op.curve_fit(abs_chi2, freqs[pts_to_use], np.abs(data_fft[pts_to_use])**2, p0=spars)
    except RuntimeError:
        bp = spars

    #bp[0] = 1
    #bp[2] = 200
    #print(bp)

    force_tilde = data_fft/chi(freqs, 1, bp[1], bp[2])
    force = np.fft.irfft(force_tilde) * cal_fac

    #remove edge effects
    force[:100] = 0
    force[-100:] = 0

    max_idx = int(len(force)/2) - 200 ## only look at the first part of the waveform to avoid
                                     ## the pulse affecting things
    force_psd = np.abs(np.fft.rfft(force[:max_idx]))**2 
    force_freqs = np.fft.rfftfreq(len(force[:max_idx]), d=time[1]-time[0])

    res_wind = np.abs(force_freqs - bp[1]/(2*np.pi)) < search_wind*4
    force_norm = np.median(np.sqrt(force_psd[res_wind]))
    #force_norm = np.std(force[:max_idx])
    #force /= force_norm
    force_lp = sp.filtfilt(*sp.butter(3, lp_freq, btype='low', fs=1/(time[1]-time[0])), force)

    search_idx_buff = 20
    force_to_search = force[(cent_time_idx-search_idx_buff):cent_time_idx]
    force_lp_to_search = force_lp[(cent_time_idx-search_idx_buff):cent_time_idx]

    amp = np.max(force_to_search) 
    amp_idx = np.argmax(force_to_search)
    print(amp, amp_idx)
    amp_lp = np.max(force_lp_to_search) 
    amp_lp_idx = np.argmax(force_lp_to_search)

    if(make_plot):
    
        if(len(ax_list) ==3):
            plt.sca(ax_list[0])
        else:
            plt.figure()
        plt.loglog(force_freqs, np.sqrt(force_psd))
        plt.plot(bp[1]/(2*np.pi), force_norm, 'ro')
        plt.xlabel("Frequency [Hz]")
        plt.ylabel("PSD [V$^2$/Hz]")
        plt.title("Pulse at time $t = %.5f$ s"%(cent_time))

        if(len(ax_list) == 3):
            plt.sca(ax_list[1])
        else:
            plt.figure()
        plt.plot(freqs, np.abs(data_fft)**2, 'ko')
        chi_psd = abs_chi2(freqs, *bp)
        plt.plot(freqs, chi_psd, 'orange')
        plt.xlim(f0_guess-search_wind, f0_guess+search_wind)
        plt.xlabel("Frequency [Hz]")
        plt.ylabel("PSD [V$^2$/Hz]")
        plt.title("Pulse at time $t = %.5f$ s"%(cent_time))
    
        if(len(ax_list) ==3):
            plt.sca(ax_list[2])
        else:
            plt.figure(figsize=(12,4))
        plt.plot(curr_time, curr_filtered_data, label="Position")
        plt.ylabel("Z position [V]")
        ax2 = plt.twinx()
        ax2.plot(curr_time, force, 'orange', label='Force')
        ax2.plot(curr_time[cent_time_idx-search_idx_buff+amp_idx], amp, 'orange', marker='o', markerfacecolor='white')
        ax2.plot(curr_time, force_lp, 'red', label="Force (filt)")
        ax2.plot(curr_time[cent_time_idx-search_idx_buff+amp_lp_idx], amp_lp, 'red', marker='o', markerfacecolor='white')
        #ax2.plot(curr_time[:max_idx], force[:max_idx], 'green', label="Prepulse")

        plt.xlabel("Time [s]")
        plt.ylabel("Force [arb units]")

        plt.legend(loc='upper left')
        plt.title("Pulse at time $t = %.5f$ s, norm = %.2e"%(cent_time, force_norm))

    return amp, amp_lp, force_norm, bp[1], bp[2]