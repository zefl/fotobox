import pyaudio
import wave
import time
        
class audio():
    def __init__(self, option):
        self.form_1 = pyaudio.paInt16 # 16-bit resolution
        self.chans = 1 # 1 channel
        self.samp_rate = 44100 # 44.1kHz sampling rate
        self.record_secs = 30 # seconds to record
        self.chunk = 4096  # 2^12 samples for buffer
        self.dev_index = 1 # device index found by p.get_device_info_by_index(ii)
        self.wav_output_filename = 'test1.wav' # name of .wav file
        self.frames = []

        self.audio = pyaudio.PyAudio() # create pyaudio instantiation
        self.stream = None
        self.stopped = False
        self.lastRead = False

      
    def sample(self):
        if self.stream == None:
            self.stream = self.audio.open(format = self.form_1,\
                            rate = self.samp_rate,\
                            channels = self.chans, \
                            input_device_index = self.dev_index,\
                            input = True, \
                            frames_per_buffer=self.chunk)
        data = self.stream.read(self.chunk)
        self.frames.append(data)
      
    def get_callback(self):        
        def callback(in_data, frame_count, time_info, status):
            if self.stopped:
                self.lastRead = True
            self.frames.append(in_data)
            return in_data, pyaudio.paContinue 
        return callback
        
        
    def start(self):
        if self.stream == None:
            #starts recording if stream gets created
            self.stream = self.audio.open(format = self.form_1,\
                    rate = self.samp_rate,\
                    channels = self.chans, \
                    input_device_index = self.dev_index,\
                    input = True, \
                    frames_per_buffer=self.chunk,
                    stream_callback=self.get_callback())
        self.frames = []
        self.stopped = False
        self.lastRead = False
        self.stream.start_stream()
        while not(self.stream.is_active()):
            pass
        
    def stop(self):
        #read out last data before stopping
        if self.stopped:
            while not(self.lastRead):
                #wait for last read of audio data
                pass
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
    
    def save(self,name):
        # save the audio frames as .wav file
        wavefile = wave.open(name,'wb')
        wavefile.setnchannels(self.chans)
        wavefile.setsampwidth(self.audio.get_sample_size(self.form_1))
        wavefile.setframerate(self.samp_rate)
        wavefile.writeframes(b''.join(self.frames))
        wavefile.close()
        self.frames = []
