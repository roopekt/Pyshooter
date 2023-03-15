# Pyshooter
A simple multiplayer shooting game. The only way to move is with the recoil of shooting. Networking is done using the relatively low level socket library (from Python's standard library).

![Players fighting](https://github.com/roopekt/Pyshooter/blob/ReadmeData/ReadmeData/gameplay.png)

## Installation 

 1. Clone the repository 
  ```shell
  git clone https://github.com/roopekt/Pyshooter.git
  ```
2. Install Python (preferably version 3.9) 

	https://www.python.org/downloads/
3. Install dependencies 
  ```shell
  pip install -r requirements.txt
  ```
  
## Usage
- Shoot by clicking, the point is to kill opponents
- A "Connection code" is used to connect clients to the host. The host should share this to others
- If the program is ran from the terminal with any arguments, the program will attempt to go straight into the game. Run `py main.py --help` for more details.

## License 

This project is distributed under the MIT License. See `LICENSE.txt` for more information.

![The lobby](https://github.com/roopekt/Pyshooter/blob/ReadmeData/ReadmeData/lobby.png)
