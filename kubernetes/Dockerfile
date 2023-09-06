FROM python:3.10-alpine

RUN pip install --no-cache-dir kubernetes

# Set the working directory to /app
WORKDIR /app

# Copy the application files to the container
COPY wait-for-reconciliation-success .

# Change the permissions of the script so it can be executed by any user
RUN chmod +x wait-for-reconciliation-success

# Add the folder to the path variable
ENV PATH="/app:${PATH}"

# Create an entrypoint that will run the script
ENTRYPOINT ["wait-for-reconciliation-success"]