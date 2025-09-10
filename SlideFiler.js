function SlideFiller() {
    // 🔹 URL do Firebase (Realtime Database → REST)
    var url = "https://slideautomathon-default-rtdb.firebaseio.com/.json";
    var response = UrlFetchApp.fetch(url);
    var data = JSON.parse(response.getContentText());
    var presentationId = "13cApJc6ZY3miQu-UYsiJFXj0v5_e1AhXoDSMT9LYoBw";
    preencherSlideComJson(data["Carlos Pereira"], presentationId);
}

function preencherSlideComJson(paciente, idOriginal) {
    // 🔹 ID da apresentação do Google Slides
    var OriginPresentation = DriveApp.getFileById(idOriginal);
    // 3️⃣ Cria uma cópia da apresentação
    var nomeCopia = paciente["nome do paciente"];
    var copia = OriginPresentation.makeCopy(nomeCopia);
    var copiaId = copia.getId();
    var presentation = SlidesApp.openById(copiaId);
    var data_semana_que_vem = getProximaTerca();
    // 🔹 Substituições
    // -- Primeiro Slide --
    presentation.replaceAllText("{{data_semana_que_vem}}", data_semana_que_vem || "__/ __/ 2025");
    // -- Segundo Slide --
    presentation.replaceAllText("{{nome}}", paciente["nome do paciente"] || "-");
    presentation.replaceAllText("{{idade}}", paciente["idade"] || "-");
    presentation.replaceAllText("{{sexo}}", paciente["sexo"] || "-");
    presentation.replaceAllText("{{etnia}}", paciente["etnia"] || "-");
    presentation.replaceAllText("{{procedente}}", paciente["procedente"] || "-");
    presentation.replaceAllText("{{data_de_nascimento}}", paciente["data de nascimento"] || "-");
    presentation.replaceAllText("{{prontuario}}", paciente["prontuario"] || "-");
    presentation.replaceAllText("{{prec_cp}}", paciente["prec-cp"] || "-");
    presentation.replaceAllText("{{contato}}", paciente["contato"] || "-");
    presentation.replaceAllText("{{posto_e_graduacao}}", paciente["posto e graduacao"] || "-");
    // -- Slide Anamnese--
    presentation.replaceAllText("{{queixa_principal}}", paciente["queixa principal"] || "-");
    presentation.replaceAllText("{{historia}}", paciente["hda"] || "-");
    presentation.replaceAllText("{{retorno1_data}}", "Retorno " + paciente["retorno1"]["data"] || "");
    presentation.replaceAllText("{{retorno1_info}}", paciente["retorno1"]["info"] || "");
    presentation.replaceAllText("{{retorno2_data}}", "Retorno " + paciente["retorno2"]["data"] || "");
    presentation.replaceAllText("{{retorno2_info}}", paciente["retorno2"]["info"] || "");
    presentation.replaceAllText("{{retorno3_data}}", "Retorno " + paciente["retorno3"]["data"] || "");
    presentation.replaceAllText("{{retorno3_info}}", paciente["retorno3"]["info"] || "");
    // -- Slide Anamnese 2 --
    // Alergias
    presentation.replaceAllText(
        "{{antecedentes_alergia}}",
        Array.isArray(paciente["antecedentes pessoais"]["alergias"])
            ? paciente["antecedentes pessoais"]["alergias"].join(" / ")
            : paciente["antecedentes pessoais"]["alergias"] || "Nega"
    );

    // Comorbidades
    presentation.replaceAllText(
        "{{antecedentes_comorbidades}}",
        Array.isArray(paciente["antecedentes pessoais"]["comorbidades"])
            ? paciente["antecedentes pessoais"]["comorbidades"].join(" / ")
            : paciente["antecedentes pessoais"]["comorbidades"] || "Nega"
    );

    // Habitos e vicios
    presentation.replaceAllText(
        "{{antecedentes_habitos_vicios}}",
        Array.isArray(paciente["antecedentes pessoais"]["habitos e vicios"])
            ? paciente["antecedentes pessoais"]["habitos e vicios"].join(" / ")
            : paciente["antecedentes pessoais"]["habitos e vicios"] || "Nega"
    );

    // Cirurgias
    presentation.replaceAllText(
        "{{antecedentes_cirurgias}}",
        Array.isArray(paciente["antecedentes pessoais"]["cirurgias previas"])
            ? paciente["antecedentes pessoais"]["cirurgias previas"].join(" / ")
            : paciente["antecedentes pessoais"]["cirurgias previas"] || "-"
    );

    // Medicamentos
    presentation.replaceAllText(
        "{{antecedentes_muc}}",
        Array.isArray(paciente["antecedentes pessoais"]["medicamentos em uso continuo"])
            ? paciente["antecedentes pessoais"]["medicamentos em uso continuo"].join(" / ")
            : paciente["antecedentes pessoais"]["medicamentos em uso continuo"] || "Nega"
    );

    // -- Slide Exame Físico --
    presentation.replaceAllText("{{peso}}", paciente["exame fisico geral"]["peso"] || "");
    presentation.replaceAllText("{{altura}}", paciente["exame fisico geral"]["altura"] || "");
    let imc = paciente["exame fisico geral"]["peso"] / paciente["exame fisico geral"]["altura"] ** 2;
    presentation.replaceAllText("{{imc}}", imc ? imc.toFixed(1) : "");
    presentation.replaceAllText("{{exame_info1}}", paciente["exame fisico geral"]["info1"] || "-");
    presentation.replaceAllText("{{exame_info2}}", paciente["exame fisico geral"]["info2"] || "-");
    // -- Slide Exame Físico --
    presentation.replaceAllText("{{exame_neuro_info1}}", paciente["exame neurologico"]["info1"] || "");
    presentation.replaceAllText("{{exame_neuro_info2}}", paciente["exame neurologico"]["info2"] || "");
    presentation.replaceAllText("{{exame_neuro_info3}}", paciente["exame neurologico"]["info3"] || "");
    presentation.replaceAllText("{{exame_neuro_info4}}", paciente["exame neurologico"]["info4"] || "");
    presentation.replaceAllText("{{exame_neuro_info5}}", paciente["exame neurologico"]["info5"] || "");
    // -- Slides exames
    var slides = presentation.getSlides();
    var slide_exame = slides[8];
    var exames = paciente["exames complementares"] || [];
    for (var i = 0; i < exames.length; i++) {
        var exame = exames[i];
        var novo_slide = slide_exame.duplicate();
        novo_slide.replaceAllText("{{exame_nome}}", exame["tipo"] || "-");
        novo_slide.replaceAllText("{{exame_data}}", exame["data"] || "-");
        novo_slide.replaceAllText("{{exame_laudo}}", exame["laudo"] || "-");
    }

    Logger.log("Slide atualizado com sucesso!");
}

function getProximaTerca() {
    var hoje = new Date();
    var diaSemana = hoje.getDay(); // 0 = domingo, 1 = segunda, ..., 6 = sábado
    var diasAteTerca = (2 - diaSemana + 7) % 7;
    diasAteTerca = diasAteTerca === 0 ? 7 : diasAteTerca; // se hoje é terça, pega a próxima
    var proximaTerca = new Date(hoje);
    proximaTerca.setDate(hoje.getDate() + diasAteTerca);
    return proximaTerca.toLocaleDateString("pt-BR");
}
