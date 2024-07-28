import yaml
import argparse

# Load the YAML configuration
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    # Load the configuration from the YAML file
    config = load_config('config.yml')

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('--panel-url', type=str, help='A URL to indicate remote operation')
    parser.add_argument('--token', type=str, help='A token for authentication')

    # Parse arguments
    args = parser.parse_args()

    # Override YAML configuration with command-line arguments if provided
    if args.remote:
        config['remote'] = args.remote
    if args.token:
        config['token'] = args.token
    print("GOOD")
    # Use the final configuration
    
if __name__ == '__main__':
    main()
