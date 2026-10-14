# Quitar fondo
    sec = self._seccion(
        side, "Quitar fondo (IA)", abierta=True, icono="ri-scissors-line"
    )
    
    # Nombres simples para el menú desplegable
    self.model_options = list(image_engine.MODELOS_REMBG.keys())
    
    # Menú desplegable para seleccionar modelo
    self.model_menu = self._crear_menu(
        sec, "Modelo (Rembg):", self.model_options, image_engine.MODELO_DEFECTO
    )
    
    # Etiqueta que muestra la descripción del modelo activo
    self.lbl_model_desc = ctk.CTkLabel(
        sec, 
        text=image_engine.MODELOS_REMBG[image_engine.MODELO_DEFECTO], 
        font=("Arial", 11), 
        text_color=MUTED, 
        wraplength=280, 
        justify="left"
    )
    self.lbl_model_desc.pack(anchor="w", padx=15, pady=(2, 6))

    # Función para actualizar la descripción si el usuario cambia el modelo en el menú
    def _actualizar_desc_modelo(eleccion):
        self.lbl_model_desc.configure(text=image_engine.MODELOS_REMBG.get(eleccion, ""))

    self.model_menu.configure(command=_actualizar_desc_modelo)

    # Opciones de refinado avanzado (Alpha Matting)
    self.chk_alpha = ctk.CTkCheckBox(
        sec, text="Refinado avanzado (Alpha Matting)", text_color=TEXT, font=("Arial", 11, "bold")
    )
    self.chk_alpha.pack(anchor="w", padx=15, pady=(8, 4))
    self.chk_alpha.select()

    self.slider_fg = self._crear_slider(sec, "Umbral Primer Plano", 200, 255, 240)
    self.slider_bg = self._crear_slider(sec, "Umbral Fondo", 0, 50, 10)

    self.btn_remove_bg = self._crear_boton(
        sec,
        "Remover Fondo con IA",
        self.ejecutar_remover_fondo,
        preview="fondo",
    )