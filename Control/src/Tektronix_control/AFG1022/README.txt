AFG1022_control contains a class that can be used to control the AFG1022 function generator. Sourced from GitHub https://github.com/asvela/tektronix-func-gen

Examples contains a few example functions also sourced from the same Github account.

Frequency_comb generates a frequency comb and exports it to the AWG. Puts it into USER0 memory slot. Also changes CH1 output to USER0 but doesn't turn it on. NOTE:  this currently has a bug which means it sometime errors when you export. I can usually fix this by changing the memory slot the signal is being saved to and running again.

sin_wave changes user input channel to sin wave. Does not turn on.

Channel_on contains functions to turn on channel 1 or channel 2.