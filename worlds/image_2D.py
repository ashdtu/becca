import matplotlib.pyplot as plt
import numpy as np

from worlds.base_world import World as BaseWorld
import worlds.world_utils as wut

class World(BaseWorld):
    """ 
    Two-dimensional visual servo task
    
    In this task, BECCA can direct its gaze up, down, left, and
    right, saccading about an block_image_data of a black square on a white
    background. It is rewarded for directing it near the center.
    The mural is not represented using basic features, but rather
    using raw inputs, which BECCA must build into features. 
    See Chapter 4 of the Users Guide for details.
    Optimal performance is a reward of around 90 reward per time step.
    """
    def __init__(self, lifespan=None):
        """ Set up the world """
        BaseWorld.__init__(self, lifespan)
        self.VISUALIZE_PERIOD = 10 ** 3
        self.FEATURE_DISPLAY_PERIOD = 10 ** 3
        self.REWARD_MAGNITUDE = 100.
        self.JUMP_FRACTION = 0.1
        self.animate = False
        self.graphing = True
        self.name = 'two dimensional visual world'
        self.name_short = 'image_2D'
        print "Entering", self.name

        self.fov_span = 10 
        # Initialize the block_image_data to be used as the environment 
        self.block_image_filename = "./images/block_test.png" 
        self.block_image_data = plt.imread(self.block_image_filename)
        # Convert it to grayscale if it's in color
        if self.block_image_data.shape[2] == 3:
            # Collapse the three RGB matrices into one b/w value matrix
            self.block_image_data = np.sum(self.block_image_data, axis=2) / 3.0
        # Define the size of the field of view, its range of 
        # allowable positions, and its initial position.
        (im_height, im_width) = self.block_image_data.shape
        im_size = np.minimum(im_height, im_width)
        self.MAX_STEP_SIZE = im_size / 2
        self.TARGET_COLUMN = im_width / 2
        self.TARGET_ROW = im_height / 2
        self.REWARD_REGION_WIDTH = im_size / 8
        self.NOISE_MAGNITUDE = 0.1
        self.FIELD_OF_VIEW_FRACTION = 0.5;
        self.fov_height =  im_size * self.FIELD_OF_VIEW_FRACTION
        self.fov_width = self.fov_height
        self.column_min = np.ceil(self.fov_width / 2)
        self.column_max = np.floor(im_width - self.column_min)
        self.row_min = np.ceil(self.fov_height / 2)
        self.row_max = np.floor(im_height - self.row_min)
        self.column_position = np.random.random_integers(self.column_min, 
                                                         self.column_max)
        self.row_position = np.random.random_integers(self.row_min, 
                                                      self.row_max)

        self.num_sensors = 2 * self.fov_span ** 2
        self.num_actions = 17
        self.sensors = np.zeros(self.num_sensors)
        self.column_history = []
        self.row_history = []
        self.last_feature_vizualized = 0
        self.step_counter = 0

    def step(self, action): 
        """ Take one time step through the world """
        self.timestep += 1
        self.action = action.ravel()
        # Actions 0-3 move the field of view to a higher-numbered 
        # row (downward in the block_image_data) with varying magnitudes, 
        # and actions 4-7 do the opposite.
        # Actions 8-11 move the field of view to a higher-numbered 
        # column (rightward in the block_image_data) with varying magnitudes, 
        # and actions 12-15 do the opposite.
        row_step    = np.round(action[0] * self.MAX_STEP_SIZE / 2 + 
                               action[1] * self.MAX_STEP_SIZE / 4 + 
                               action[2] * self.MAX_STEP_SIZE / 8 + 
                               action[3] * self.MAX_STEP_SIZE / 16 - 
                               action[4] * self.MAX_STEP_SIZE / 2 - 
                               action[5] * self.MAX_STEP_SIZE / 4 - 
                               action[6] * self.MAX_STEP_SIZE / 8 - 
                               action[7] * self.MAX_STEP_SIZE / 16)
        column_step = np.round(action[8] * self.MAX_STEP_SIZE / 2 + 
                               action[9] * self.MAX_STEP_SIZE / 4 + 
                               action[10] * self.MAX_STEP_SIZE / 8 + 
                               action[11] * self.MAX_STEP_SIZE / 16 - 
                               action[12] * self.MAX_STEP_SIZE / 2 - 
                               action[13] * self.MAX_STEP_SIZE / 4 - 
                               action[14] * self.MAX_STEP_SIZE / 8 - 
                               action[15] * self.MAX_STEP_SIZE / 16)
        
        row_step = np.round(row_step * (
                1 + self.NOISE_MAGNITUDE * np.random.random_sample() * 2.0 - 
                self.NOISE_MAGNITUDE * np.random.random_sample() * 2.0))
        column_step = np.round(column_step * (
                1 + self.NOISE_MAGNITUDE * np.random.random_sample() * 2.0 - 
                self.NOISE_MAGNITUDE * np.random.random_sample() * 2.0))
        self.row_position = self.row_position + int(row_step)
        self.column_position = self.column_position + int(column_step)
        # Respect the boundaries of the block_image_data
        self.row_position = max(self.row_position, self.row_min)
        self.row_position = min(self.row_position, self.row_max)
        self.column_position = max(self.column_position, self.column_min)
        self.column_position = min(self.column_position, self.column_max)

        # At random intervals, jump to a random position in the world
        if np.random.random_sample() < self.JUMP_FRACTION:
            self.column_position = np.random.random_integers(self.column_min, 
                                                             self.column_max)
            self.row_position = np.random.random_integers(self.row_min, 
                                                          self.row_max)
        # Create the sensory input vector
        fov = self.block_image_data[self.row_position - self.fov_height / 2: 
                                    self.row_position + self.fov_height / 2, 
                                    self.column_position - self.fov_width / 2: 
                                    self.column_position + self.fov_width / 2]
        center_surround_pixels = wut.center_surround(fov,self.fov_span)
        unsplit_sensors = center_surround_pixels.ravel()
        sensors = np.concatenate((np.maximum(unsplit_sensors, 0), 
                                  np.abs(np.minimum(unsplit_sensors, 0)) ))
        
        self.reward = 0
        if ((np.abs(self.column_position - self.TARGET_COLUMN) < 
             self.REWARD_REGION_WIDTH / 2) and 
            (np.abs(self.row_position - self.TARGET_ROW) < 
             self.REWARD_REGION_WIDTH / 2)):
            self.reward += self.REWARD_MAGNITUDE
        return sensors, self.reward
     
    def set_agent_parameters(self, agent):
        agent.reward_min = 0.
        agent.reward_max = 100.
        return

    def visualize(self, agent):
        """ Show what is going on in BECCA and in the world """
        if self.animate:
            print ''.join([str(self.row_position), ', ', 
                           str(self.column_position), 
                           '-row and col position  ', 
                           str(self.reward), '-reward'])
        if not self.graphing:
            return

        # Periodically display the history and inputs as perceived by BECCA
        self.row_history.append(self.row_position)
        self.column_history.append(self.column_position)
        if (self.timestep % self.VISUALIZE_PERIOD) == 0:
            print("world is %s timesteps old" % self.timestep)
            fig = plt.figure(11)
            plt.clf()
            plt.plot( self.row_history, 'k.')    
            plt.title("Row history")
            plt.xlabel('time step')
            plt.ylabel('position (pixels)')
            fig.show()
            fig.canvas.draw()

            fig = plt.figure(12)
            plt.clf()
            plt.plot( self.column_history, 'k.')    
            plt.title("Column history")
            plt.xlabel('time step')
            plt.ylabel('position (pixels)')
            fig.show()
            fig.canvas.draw()

            fig = plt.figure(13)
            sensed_image = np.reshape(0.5 * (
                    self.sensors[:len(self.sensors)/2] - 
                    self.sensors[len(self.sensors)/2:] + 1), 
                    (self.fov_span, self.fov_span))
            plt.gray()
            plt.imshow(sensed_image, interpolation='nearest')
            plt.title("Image sensed")
            fig.show()
            fig.canvas.draw()

        # Periodcally show the entire feature set 
        if self.timestep % self.FEATURE_DISPLAY_PERIOD == 0:
            feature_set = agent.get_projections()
            level_index = -1
            for level in feature_set:
                level_index += 1
                feature_index = -1
                for feature in level:
                    feature_index += 1
                    wut.vizualize_pixel_array_feature(
                            feature[self.num_actions:,:], 
                            level_index, feature_index, 
                            world_name=self.name_short) 
        return
