# See https://www.tensorflow.org/tutorials/keras/text_classification
import numpy as np
import os
import re
import string

from pathlib import Path

import tensorflow as tf
from keras import layers, losses


def custom_standardization(input_data):
    lowercase = tf.strings.lower(input_data)
    return tf.strings.regex_replace(lowercase, '[%s]' % re.escape(string.punctuation), '')


custom_objects = {"custom_standardization": custom_standardization}


def create_model(model_path, train_data_folder, test_data_folder):
    batch_size = 32
    seed = 42

    data_dir = train_data_folder
    raw_train_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='training',
        seed=seed)

    print("Label 0 corresponds to", raw_train_ds.class_names[0])
    print("Label 1 corresponds to", raw_train_ds.class_names[1])

    raw_val_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='validation',
        seed=seed,
        shuffle=False)

    raw_test_ds = tf.keras.utils.text_dataset_from_directory(
        test_data_folder,
        batch_size=batch_size)

    max_features = 10000
    sequence_length = 250

    vectorize_layer = layers.TextVectorization(
        standardize=custom_standardization,
        max_tokens=max_features,
        output_mode='int',
        output_sequence_length=sequence_length)

    train_text = raw_train_ds.map(lambda x, y: x)
    vectorize_layer.adapt(train_text)

    def vectorize_text(text, label):
        text = tf.expand_dims(text, -1)
        return vectorize_layer(text), label

    text_batch, label_batch = next(iter(raw_train_ds))
    first_trace, first_label = text_batch[0], label_batch[0]
    print("Trace", first_trace)
    print("Label", raw_train_ds.class_names[first_label])
    print("Vectorized trace", vectorize_text(first_trace, first_label))

    print('Vocabulary size: {}'.format(len(vectorize_layer.get_vocabulary())))

    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)
    test_ds = raw_test_ds.map(vectorize_text)

    embedding_dim = 16
    model = tf.keras.Sequential([
        layers.Embedding(max_features + 1, embedding_dim),
        layers.Dropout(0.2),
        layers.GlobalAveragePooling1D(),
        layers.Dropout(0.2),
        layers.Dense(1)])

    model.summary()

    model.compile(loss=losses.BinaryCrossentropy(from_logits=True),
                  optimizer='adam',
                  metrics=tf.metrics.BinaryAccuracy(threshold=0.0))

    epochs = 10
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs)

    loss, accuracy = model.evaluate(test_ds)
    print("Loss: ", loss)
    print("Accuracy: ", accuracy)

    export_model = tf.keras.Sequential([
      vectorize_layer,
      model,
      layers.Activation('sigmoid')
    ])

    export_model.compile(
        loss=losses.BinaryCrossentropy(from_logits=False), optimizer="adam", metrics=['accuracy']
    )
    export_model.save(model_path)


if __name__ == '__main__':
    tf.config.set_visible_devices([], 'GPU')

    model_path = os.path.dirname(os.path.realpath(__file__)) + "/model/trace_model"
    trace_model = None
    if not os.path.isdir(model_path):
        create_model(model_path, "/tmp/trace-data-Bd4pvA/train", "/tmp/trace-data-Bd4pvA/test")

    trace_model = tf.keras.models.load_model(model_path, custom_objects=custom_objects)

    samples_to_predict = np.array(
        ["success", "failed", "I Failed my vocabulary test", "Success is not an option"])

    predictions = trace_model.predict(samples_to_predict, verbose=2)
    test = (predictions > 0.5).astype('int32')
    print(test)
