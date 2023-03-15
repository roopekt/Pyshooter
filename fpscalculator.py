import time

NEW_FRAME_WHEIGHT = 1/3

class FPSCalculator:

    def __init__(self):
        self.current_FPS = None
        self.reported_FPS = self.current_FPS # FPS reported outside is only updated once a second
        self.last_reported_FPS_update_time = -1

    def get_FPS_str(self, this_frame_delta_time: float):
        this_frame_delta_time = max(1e-6, this_frame_delta_time)
        this_frame_FPS = 1 / this_frame_delta_time
        
        if self.current_FPS == None:
            self.current_FPS = this_frame_FPS
        else:
            self.current_FPS = NEW_FRAME_WHEIGHT * this_frame_FPS + (1 - NEW_FRAME_WHEIGHT) * self.current_FPS

        now = time.time()
        if now - self.last_reported_FPS_update_time > 1:
            self.reported_FPS = self.current_FPS
            self.last_reported_FPS_update_time = now

        return "%.1f" % self.reported_FPS
